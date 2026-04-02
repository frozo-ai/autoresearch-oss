"""Core ratchet loop engine — the heart of autoresearch.

The loop:
1. Read program.md for strategy
2. Ask LLM to propose a change to the target file
3. Apply the change
4. Run the eval harness
5. If score improved: keep (git merge to best branch)
6. If score didn't improve: revert (discard experiment branch)
7. Log result to results.tsv
8. Repeat until max_experiments or time limit
"""

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

from runner.git_ratchet import GitRatchet
from runner.program_parser import ParseError, ProgramConfig, parse_file
from runner.results import ExperimentResult, ResultsLog
from runner.strategy import LoopStrategy

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis_client():
    """Lazy-init Redis client for cancel/pause checks."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=False)
        return _redis_client
    except Exception:
        return None


def _check_cancel_flag(run_id: str) -> bool:
    """Check if this run has been cancelled via Redis flag."""
    client = _get_redis_client()
    if client is None:
        return False
    try:
        return client.get(f"run:{run_id}:cancel") == b"1"
    except Exception:
        return False


def _check_stagnation(kept_history: list[bool], window: int = 15) -> bool:
    """Check if the last `window` experiments were all reverted (no improvement)."""
    if len(kept_history) < window:
        return False
    return not any(kept_history[-window:])


class EvalCache:
    """In-memory cache keyed by SHA-256 of target file content.

    Avoids re-running eval when the LLM proposes identical content.
    Scope: per-run only (eval harness may change between runs).
    """

    def __init__(self):
        self._cache: dict[str, tuple[float, bool, int]] = {}  # hash -> (score, crashed, exp_num)

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def lookup(self, content: str) -> tuple[float, bool, int] | None:
        return self._cache.get(self._hash(content))

    def record(self, content: str, score: float, crashed: bool, exp_num: int) -> None:
        self._cache[self._hash(content)] = (score, crashed, exp_num)


def _get_llm_client(provider: str):
    """Get the appropriate LLM client based on provider."""
    if provider == "anthropic":
        import anthropic

        return anthropic.Anthropic()
    elif provider == "openai":
        import openai

        return openai.OpenAI()
    elif provider == "gemini":
        import google.generativeai as genai

        api_key = os.environ.get("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        genai.configure(api_key=api_key)
        return genai
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _propose_change(
    client,
    provider: str,
    model: str,
    program: ProgramConfig,
    target_content: str,
    results_so_far: str,
    target_file_path: str,
    memory_context: str = "",
    mode_prompt: str = "",
    temperature: float = 1.0,
) -> tuple[str, str]:
    """Ask the LLM to propose a change to the target file.

    Returns:
        Tuple of (new_content, description)
    """
    system_prompt = f"""You are an autonomous research agent running an experiment loop.

Your goal: {program.goal}

Constraints:
{chr(10).join(f'- {c}' for c in program.constraints)}

You are optimizing the file: {target_file_path}
Metric: {program.metric_name} ({"higher" if program.higher_is_better else "lower"} is better)

Previous experiment results:
{results_so_far or "No experiments run yet — this is the first attempt."}

Propose a SINGLE, focused change to improve the metric. Be creative but systematic.
Return your response as JSON with exactly two fields:
- "description": A one-line description of what you changed and why
- "content": The complete new content of the target file

Return ONLY valid JSON, no markdown fencing."""

    if memory_context:
        system_prompt += f"\n\n{memory_context}"
    if mode_prompt:
        system_prompt += f"\n\n{mode_prompt}"

    user_prompt = f"""Current content of {target_file_path}:

{target_content}

Propose your next experiment. Return JSON with "description" and "content" fields."""

    if provider == "anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
    elif provider == "openai":
        response = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content
    elif provider == "gemini":
        model_obj = client.GenerativeModel(model)
        response = model_obj.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config={"temperature": temperature},
        )
        text = response.text
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    # Strip markdown fencing if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    parsed = json.loads(text)
    return parsed["content"], parsed["description"]


def _run_eval(eval_command: str, metric_name: str, cwd: Path) -> tuple[float, bool]:
    """Run the eval harness and parse the score.

    Returns:
        Tuple of (score, crashed)
    """
    import subprocess

    time_budget = int(os.environ.get("TIME_BUDGET", "300"))

    try:
        result = subprocess.run(
            eval_command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=time_budget,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Eval timed out after %ds", time_budget)
        return 0.0, True

    if result.returncode != 0:
        logger.warning("Eval failed (exit code %d): %s", result.returncode, result.stderr[:500])
        return 0.0, True

    # Parse metric from stdout: "metric_name:value"
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith(f"{metric_name}:"):
            try:
                score = float(line.split(":", 1)[1].strip())
                return score, False
            except ValueError:
                logger.warning("Could not parse score from line: %s", line)
                return 0.0, True

    logger.warning("Metric '%s' not found in eval output", metric_name)
    return 0.0, True


def run_loop(
    workspace: str | Path = ".",
    program_path: str = "program.md",
    target_file: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    max_experiments: int = 100,
    eval_command: str | None = None,
    on_experiment_complete: callable | None = None,
    stagnation_window: int = 15,
    min_experiments: int = 10,
    plateau_detection: bool = True,
    memory_context: str = "",
    strategy_override: str = "auto",
) -> ResultsLog:
    """Run the autonomous experiment loop.

    Args:
        workspace: Path to the project workspace
        program_path: Path to program.md relative to workspace
        target_file: Path to the target file to optimize (overrides program.md)
        provider: LLM provider (anthropic, openai, gemini)
        model: LLM model name
        max_experiments: Maximum number of experiments to run
        eval_command: Eval command (overrides program.md)

    Returns:
        ResultsLog with all experiment results
    """
    workspace = Path(workspace).resolve()
    os.chdir(workspace)

    # Parse program.md for loop context
    program_file = workspace / program_path
    try:
        program = parse_file(program_file)
    except (ParseError, FileNotFoundError) as e:
        # program.md may be AI-generated without strict format — use defaults
        # The eval_command, target_file, provider, model are all passed as args
        logger.info("Using default program config (program.md parse: %s)", e)
        raw = program_file.read_text() if program_file.exists() else ""
        program = ProgramConfig(
            title="AutoResearch Run",
            goal=raw[:200] if raw else "Optimize the target file",
            metric_name="accuracy_pct",
            higher_is_better=True,
            raw_content=raw,
        )
    logger.info("Loaded program: %s", program.title)
    logger.info("Goal: %s", program.goal)
    logger.info("Metric: %s (higher_is_better=%s)", program.metric_name, program.higher_is_better)

    # Resolve provider and model from env or args
    provider = provider or os.environ.get("LLM_PROVIDER", "anthropic")
    model = model or os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
    eval_cmd = eval_command or program.eval_command

    if not eval_cmd:
        raise ValueError("No eval command found in program.md or --eval-command flag")

    # Determine target file
    # Look for it in program.md constraints or use provided value
    if not target_file:
        # Try to infer from constraints (look for "DO NOT MODIFY" pattern)
        for constraint in program.constraints:
            if "DO NOT MODIFY" in constraint.upper():
                # The file mentioned is the eval harness, not the target
                continue
        # Default: look for common target file names
        candidates = list(workspace.glob("*prompt*")) + list(workspace.glob("*config*"))
        if candidates:
            target_file = str(candidates[0].relative_to(workspace))
        else:
            raise ValueError("Could not determine target file. Use --target-file flag.")

    target_path = workspace / target_file
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_path}")

    logger.info("Target file: %s", target_file)
    logger.info("Eval command: %s", eval_cmd)
    logger.info("Provider: %s / %s", provider, model)
    logger.info("Max experiments: %d", max_experiments)

    # Setup git ratchet
    ratchet = GitRatchet(workspace)
    ratchet.setup_best_branch()

    # Setup results log
    results = ResultsLog(workspace / "results.tsv")

    # Get LLM client
    client = _get_llm_client(provider)

    # Run baseline eval
    logger.info("Running baseline eval...")
    baseline_score, baseline_crashed = _run_eval(eval_cmd, program.metric_name, workspace)
    if baseline_crashed:
        logger.error("Baseline eval crashed — cannot proceed. Fix eval harness and retry.")
        sys.exit(1)

    logger.info("Baseline score: %.4f", baseline_score)
    current_best_score = baseline_score
    kept_history: list[bool] = []
    eval_cache = EvalCache()
    strategy = LoopStrategy(override=strategy_override)

    # Main experiment loop
    for exp_num in range(1, max_experiments + 1):
        # Check for user cancellation
        run_id = os.environ.get("RUN_ID", "")
        if run_id and _check_cancel_flag(run_id):
            logger.info("Run cancelled by user after %d experiments", exp_num - 1)
            break

        logger.info("=" * 60)
        logger.info("Experiment %d/%d", exp_num, max_experiments)
        logger.info("=" * 60)

        start_time = time.time()
        description = ""
        score = 0.0
        crashed = False
        crash_message = ""
        commit_hash = ""
        kept = False
        mode = strategy.get_mode()

        try:
            # Create experiment branch
            branch = ratchet.create_experiment_branch(exp_num)

            # Read current target file
            target_content = target_path.read_text()

            # Build results context for LLM
            results_context = ""
            if results.results:
                last_5 = results.results[-5:]
                results_context = "\n".join(
                    f"  Exp {r.experiment_number}: {r.description} → "
                    f"score={r.score:.2f}, delta={r.delta:+.2f}, kept={r.kept}"
                    for r in last_5
                )

            # Propose change
            logger.info("Proposing change via %s/%s (mode=%s)...", provider, model, mode)
            new_content, description = _propose_change(
                client, provider, model, program,
                target_content, results_context, target_file,
                memory_context=memory_context,
                mode_prompt=strategy.get_prompt_addition(),
                temperature=strategy.get_temperature(),
            )

            # Apply change
            target_path.write_text(new_content)
            commit_hash = ratchet.commit_changes(f"exp-{exp_num:04d}: {description}")

            # Check eval cache — skip if identical content was already evaluated
            cached_result = eval_cache.lookup(new_content)
            if cached_result is not None:
                cached_score, cached_crashed, orig_exp = cached_result
                logger.info(
                    "CACHE HIT — identical to experiment #%d (score: %.4f). Skipping eval.",
                    orig_exp, cached_score,
                )
                ratchet.revert(branch)
                duration = int(time.time() - start_time)
                result = ExperimentResult(
                    experiment_number=exp_num,
                    description=f"(cached) {description}",
                    score=cached_score,
                    baseline_score=baseline_score,
                    delta=cached_score - baseline_score,
                    kept=False,
                    duration_seconds=0,
                    commit_hash=commit_hash,
                    crashed=cached_crashed,
                    crash_message="",
                    cached=True,
                )
                results.append(result)
                kept_history.append(False)
                continue

            # Run eval
            logger.info("Running eval: %s", eval_cmd)
            score, crashed = _run_eval(eval_cmd, program.metric_name, workspace)
            eval_cache.record(new_content, score, crashed, exp_num)

            if crashed:
                crash_message = "Eval harness crashed or timed out"
                logger.warning("Eval crashed for experiment %d", exp_num)
                ratchet.revert(branch)
            else:
                delta = score - current_best_score
                is_improvement = (
                    delta > 0 if program.higher_is_better else delta < 0
                )

                if is_improvement:
                    kept = True
                    ratchet.keep(branch)
                    current_best_score = score
                    logger.info(
                        "KEPT — score: %.4f (delta: %+.4f) — %s",
                        score, delta, description,
                    )
                else:
                    ratchet.revert(branch)
                    logger.info(
                        "REVERTED — score: %.4f (delta: %+.4f) — %s",
                        score, delta, description,
                    )

        except json.JSONDecodeError as e:
            crashed = True
            crash_message = f"LLM returned invalid JSON: {e}"
            logger.warning("JSON parse error: %s", e)
            strategy.record(False)
            # Revert any partial changes
            try:
                ratchet.revert(ratchet.get_current_branch())
            except Exception:
                ratchet._run("checkout", ratchet.best_branch, check=False)
        except Exception as e:
            crashed = True
            crash_message = str(e)
            logger.exception("Experiment %d failed: %s", exp_num, e)
            strategy.record(False)
            try:
                ratchet.revert(ratchet.get_current_branch())
            except Exception:
                ratchet._run("checkout", ratchet.best_branch, check=False)

        duration = int(time.time() - start_time)

        # Record strategy outcome (only once — exceptions above record False directly)
        if not crashed:
            strategy.record(kept)

        # Log result
        result = ExperimentResult(
            experiment_number=exp_num,
            description=description or "(no description)",
            score=score,
            baseline_score=baseline_score,
            delta=score - baseline_score,
            kept=kept,
            duration_seconds=duration,
            commit_hash=commit_hash,
            crashed=crashed,
            crash_message=crash_message,
            mode=mode,
        )
        results.append(result)
        kept_history.append(kept)

        # Check for plateau — early stop if stuck
        if plateau_detection and exp_num >= min_experiments:
            if _check_stagnation(kept_history, stagnation_window):
                logger.info(
                    "Plateau detected — no improvement in last %d experiments. Stopping early at %d/%d.",
                    stagnation_window, exp_num, max_experiments,
                )
                break

        logger.info(
            "Experiment %d complete: score=%.4f, kept=%s, duration=%ds",
            exp_num, score, kept, duration,
        )

        # Notify caller of experiment completion (for CLI progress display)
        if on_experiment_complete:
            try:
                on_experiment_complete(result, exp_num, max_experiments)
            except Exception:
                pass  # Don't let callback errors break the loop

    # Final summary
    logger.info("=" * 60)
    logger.info("RUN COMPLETE")
    logger.info(results.summary())
    logger.info("Best diff saved. Run 'ars diff' to view.")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_loop()
