"""ars run — execute the autonomous experiment loop."""

import json
import logging
import os
import time
from pathlib import Path

import click
import httpx

FREE_LOCAL_MAX_EXPERIMENTS = 25
CONFIG_FILE = Path.home() / ".autoresearch" / "config.json"


def _is_logged_in() -> dict | None:
    """Check if user is logged in. Returns config dict or None."""
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text())
        if config.get("token"):
            return config
    return None


def _show_upsell(was_capped: bool):
    """Show upsell message after a capped or completed run."""
    if was_capped:
        click.echo("")
        click.echo("=" * 60)
        click.echo(f"  FREE LIMIT: {FREE_LOCAL_MAX_EXPERIMENTS} experiments per run.")
        click.echo("  Sign in for unlimited local experiments (free):")
        click.echo("    ars login")
        click.echo("")
        click.echo("  Or run on the cloud with parallel lanes:")
        click.echo("    ars run --cloud --max-experiments 100")
        click.echo("    ars upgrade  → plans from $9/mo")
        click.echo("=" * 60)
    else:
        click.echo("")
        click.echo("  Run on the cloud for parallel lanes & dashboard:")
        click.echo("    ars run --cloud --lanes 4")
        click.echo("    ars upgrade  → plans from $9/mo")


@click.command("run")
@click.option("--program", "-p", default="program.md", help="Path to program.md")
@click.option("--target-file", "-f", default=None, help="Target file to optimize")
@click.option("--provider", default=None, help="LLM provider (anthropic, openai, gemini)")
@click.option("--model", "-m", default=None, help="LLM model name")
@click.option("--max-experiments", "-n", default=100, help="Max experiments to run")
@click.option("--eval-command", "-e", default=None, help="Eval command (overrides program.md)")
@click.option("--cloud", is_flag=True, help="Run on AutoResearch Cloud (requires login)")
@click.option("--lanes", default=1, help="Parallel lanes (cloud only)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
@click.option("--dry-run", is_flag=True, help="Validate setup and run baseline eval only (no experiments)")
def run_cmd(
    program: str,
    target_file: str | None,
    provider: str | None,
    model: str | None,
    max_experiments: int,
    eval_command: str | None,
    cloud: bool,
    lanes: int,
    verbose: bool,
    dry_run: bool,
):
    """Run the autonomous experiment loop.

    Reads program.md, proposes changes via LLM, runs eval harness,
    keeps improvements, reverts failures. Repeats until max experiments.

    Shows estimated API cost before starting. Use --dry-run to validate
    your setup (parses program.md, runs baseline eval) without running
    any experiments.

    Free local runs are limited to 25 experiments. Sign in with
    'ars login' for unlimited local runs, or use --cloud for
    cloud execution with parallel lanes.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    # Use session defaults if provider/model not specified
    if not provider and not os.environ.get("LLM_PROVIDER"):
        try:
            from cli.session import get_last_provider
            provider = get_last_provider()
        except Exception:
            pass
    if not model and not os.environ.get("LLM_MODEL"):
        try:
            from cli.session import get_last_model
            model = get_last_model()
        except Exception:
            pass

    if cloud:
        _run_cloud(program, target_file, provider, model, max_experiments, eval_command, lanes)
        return

    # --- Local execution ---
    config = _is_logged_in()
    was_capped = False

    if not config:
        # Anonymous user — cap at FREE_LOCAL_MAX_EXPERIMENTS
        if max_experiments > FREE_LOCAL_MAX_EXPERIMENTS:
            click.echo(
                f"Free local limit: {FREE_LOCAL_MAX_EXPERIMENTS} experiments. "
                f"Run 'ars login' for unlimited."
            )
            max_experiments = FREE_LOCAL_MAX_EXPERIMENTS
            was_capped = True

    from runner.loop import run_loop

    # Show cost estimate before starting
    try:
        target_path = Path(".") / (target_file or "system_prompt.txt")
        target_content = target_path.read_text() if target_path.exists() else ""
        program_content = Path(program).read_text() if Path(program).exists() else ""
        _provider = provider or os.environ.get("LLM_PROVIDER", "anthropic")
        _model = model or os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")

        # Simple token estimate: ~3.5 chars per token
        target_tokens = max(1, int(len(target_content) / 3.5))
        program_tokens = max(1, int(len(program_content) / 3.5))
        per_exp = 500 + program_tokens + target_tokens * 2 + 200  # system + program + target(in+out) + context
        total_tokens = per_exp * max_experiments

        # Price per million tokens (input estimate — output is ~same for haiku-class)
        prices = {
            "claude-haiku-4-5-20251001": 3.0, "claude-haiku-4-5": 3.0,
            "claude-sonnet-4-6": 9.0, "gpt-4o-mini": 0.375, "gpt-4o": 6.25,
            "gemini-1.5-flash": 0.2, "gemini-1.5-pro": 3.1,
        }
        price_per_m = prices.get(_model, 3.0)
        est_low = round(total_tokens / 1_000_000 * price_per_m, 2)
        est_high = round(est_low * 2, 2)

        click.echo(f"\n  Provider: {_provider} / {_model}")
        click.echo(f"  Experiments: {max_experiments}")
        click.echo(f"  Estimated API cost: ${est_low:.2f} - ${est_high:.2f}")
        click.echo(f"  (charged to your API key, not AutoResearch)\n")
    except Exception:
        pass  # Don't block run if estimate fails

    if dry_run:
        click.echo("Dry run — validating setup...")
        try:
            from runner.program_parser import parse_file
            config = parse_file(program)
            click.echo(f"  program.md: OK (goal: {config.goal[:60]})")
            click.echo(f"  metric: {config.metric_name} (higher_is_better={config.higher_is_better})")
        except Exception as e:
            click.echo(f"  program.md: {click.style('WARN', fg='yellow')} — {e}")
            click.echo("  (will use defaults from --target-file and --eval-command flags)")

        # Run baseline eval once
        eval_cmd = eval_command
        if not eval_cmd:
            for name in ["eval.py", "eval.sh"]:
                if Path(name).exists():
                    eval_cmd = f"python3 eval.py" if name == "eval.py" else f"bash eval.sh"
                    break
        if eval_cmd:
            import subprocess
            click.echo(f"\n  Running baseline eval: {eval_cmd}")
            result = subprocess.run(eval_cmd, shell=True, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                click.echo(f"  {click.style('PASS', fg='green')} — eval exited cleanly")
                # Try to find the metric
                for line in result.stdout.splitlines():
                    if ":" in line and any(c.isdigit() for c in line):
                        click.echo(f"  Output: {line.strip()}")
            else:
                click.echo(f"  {click.style('FAIL', fg='red')} — eval exited with code {result.returncode}")
                if result.stderr:
                    click.echo(f"  stderr: {result.stderr[:200]}")
        else:
            click.echo(f"  No eval script found (eval.py or eval.sh)")

        click.echo(f"\n  Setup looks {'good' if eval_cmd else 'incomplete'}. Run 'ars run' to start experiments.")
        return

    def _on_experiment(result, exp_num, total):
        """Print live progress for each experiment."""
        kept_str = click.style("KEPT  ", fg="green", bold=True) if result.kept else click.style("revert", fg="red")
        score_str = f"score={result.score:.1f}"
        delta_str = f"({result.delta:+.1f})"
        if result.delta > 0:
            delta_str = click.style(delta_str, fg="green")
        elif result.delta < 0:
            delta_str = click.style(delta_str, fg="red")
        desc = (result.description or "")[:50]
        click.echo(f"  Exp {exp_num}/{total} {kept_str} {score_str} {delta_str} {result.duration_seconds}s  {desc}")

    try:
        results = run_loop(
            workspace=".",
            program_path=program,
            target_file=target_file,
            provider=provider,
            model=model,
            max_experiments=max_experiments,
            eval_command=eval_command,
            on_experiment_complete=_on_experiment,
        )
        click.echo(f"\n{results.summary()}")

        # Update session state
        try:
            from cli.session import update_after_run
            _best = results.best_result
            _baseline = results.results[0].baseline_score if results.results else None
            update_after_run(
                workspace=str(Path(".").resolve()),
                provider=provider or os.environ.get("LLM_PROVIDER", "anthropic"),
                model=model or os.environ.get("LLM_MODEL", ""),
                max_experiments=max_experiments,
                total=results.total_count,
                kept=results.kept_count,
                best_score=_best.score if _best else None,
                baseline=_baseline,
            )
        except Exception:
            pass  # Non-critical

        if results.kept_count > 0:
            click.echo("\n  ars results  — view all experiments")
            click.echo("  ars diff     — see what changed")
            click.echo("  ars apply    — apply best version")

        _show_upsell(was_capped)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nRun cancelled by user.")
        raise SystemExit(0)


def _run_cloud(
    program: str,
    target_file: str | None,
    provider: str | None,
    model: str | None,
    max_experiments: int,
    eval_command: str | None,
    lanes: int,
):
    """Execute a run on AutoResearch Cloud."""
    config = _is_logged_in()
    if not config:
        click.echo("Not logged in. Run 'ars login' first.")
        raise SystemExit(1)

    api_url = config.get("api_url", "https://api.research.frozo.ai/v1")
    token = config["token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Resolve provider and API key
    provider = provider or os.environ.get("LLM_PROVIDER", "openai")
    api_key = os.environ.get(
        {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GOOGLE_API_KEY"}.get(provider, "LLM_API_KEY"),
        "",
    )
    if not api_key:
        api_key = click.prompt(f"Enter your {provider} API key", hide_input=True)

    model = model or os.environ.get("LLM_MODEL")

    # Read local project files
    workspace = Path(".")
    program_path = workspace / program
    if not program_path.exists():
        click.echo(f"Error: {program} not found. Run 'ars init' first.", err=True)
        raise SystemExit(1)

    program_md = program_path.read_text()

    # Detect target file
    if not target_file:
        for name in ["system_prompt.txt", "prompt.txt", "config.yaml", "target.txt"]:
            if (workspace / name).exists():
                target_file = name
                break
    if not target_file:
        click.echo("Error: Could not detect target file. Use --target-file.", err=True)
        raise SystemExit(1)

    target_content = (workspace / target_file).read_text()

    # Detect eval script
    eval_script = ""
    eval_type = "bash"
    for name, etype in [("eval.py", "python_script"), ("eval.sh", "bash")]:
        if (workspace / name).exists():
            eval_script = (workspace / name).read_text()
            eval_type = etype
            break

    # Step 1: Create project on cloud
    click.echo(f"\n  Files to upload:")
    click.echo(f"    program.md: {len(program_md)} chars")
    click.echo(f"    target: {target_file} ({len(target_content)} chars)")
    if eval_script:
        click.echo(f"    eval: {'eval.py' if eval_type == 'python_script' else 'eval.sh'} ({len(eval_script)} chars)")
    else:
        click.echo(f"    eval: {click.style('none found', fg='yellow')} (will use cloud defaults)")
    click.echo()
    click.echo(f"Deploying to AutoResearch Cloud...")
    try:
        resp = httpx.post(
            f"{api_url}/projects/",
            headers=headers,
            json={
                "name": workspace.resolve().name,
                "target_file_path": target_file,
                "eval_type": eval_type,
                "program_md": program_md,
                "eval_config": {
                    "target_content": target_content,
                    "eval_script": eval_script,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        project = resp.json()
        project_id = project["id"]
        click.echo(f"  Project: {project['name']} ({project_id[:8]}...)")
    except httpx.HTTPStatusError as e:
        click.echo(f"Error creating project: {e.response.text}", err=True)
        raise SystemExit(1)

    # Step 2: Trigger run
    click.echo(f"Starting run ({max_experiments} experiments, {lanes} lane(s))...")
    try:
        resp = httpx.post(
            f"{api_url}/projects/{project_id}/runs/",
            headers=headers,
            json={
                "llm_provider": provider,
                "llm_api_key": api_key,
                "llm_model": model,
                "max_experiments": max_experiments,
                "parallel_lanes": lanes,
            },
            timeout=30,
        )
        resp.raise_for_status()
        run = resp.json()
        run_id = run["id"]
        click.echo(f"  Run: {run['tag']} ({run_id[:8]}...)")
    except httpx.HTTPStatusError as e:
        click.echo(f"Error starting run: {e.response.text}", err=True)
        raise SystemExit(1)

    # Step 3: Poll for results
    click.echo(f"\nPolling for results...")
    try:
        while True:
            time.sleep(10)
            resp = httpx.get(f"{api_url}/runs/{run_id}", headers=headers, timeout=10)
            data = resp.json()
            status = data.get("status", "unknown")
            total = data.get("total_experiments", 0)
            kept = data.get("improvements_kept", 0)
            best = data.get("best_score")

            click.echo(
                f"  {status}: {total}/{max_experiments} experiments, "
                f"{kept} kept, best={best or '--'}"
            )

            if status in ("completed", "failed", "cancelled"):
                break
    except KeyboardInterrupt:
        click.echo("\nStopped polling. Run continues on the cloud.")
        click.echo(f"  Check status: ars status --cloud {run_id}")

    # Step 4: Show results
    click.echo("")
    if status == "completed":
        baseline = data.get("baseline_score")
        improvement = data.get("improvement_pct")
        click.echo(f"Run complete!")
        click.echo(f"  Baseline:    {baseline}")
        click.echo(f"  Best Score:  {best}")
        click.echo(f"  Improvement: {'+' if improvement and improvement > 0 else ''}{improvement or 0:.1f}%")
        click.echo(f"  Experiments: {total} ({kept} kept)")
    elif status == "failed":
        click.echo(f"Run failed: {data.get('error_message', 'Unknown error')}")

    # Dashboard link
    frontend_url = api_url.replace("/v1", "").replace("api-", "web-").replace("api.", "")
    click.echo(f"\n  View on dashboard: {frontend_url}/dashboard/{project_id}/runs/{run_id}")
