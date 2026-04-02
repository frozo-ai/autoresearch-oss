#!/usr/bin/env python3
"""Universal LLM judge eval — auto-detects provider from environment.

Works with Anthropic, OpenAI, and Gemini. Uses whichever API key is
available in the environment (set by the runner from the user's BYOK key).

Usage in eval config:
  metric_name: quality_score (or accuracy_pct, etc.)
  higher_is_better: true
  rubric: "Rate on clarity, accuracy, and usefulness"
  criteria: "clarity,accuracy,usefulness"

Prints: metric_name:score to stdout.
"""

import json
import os
import sys


def _detect_provider():
    """Auto-detect LLM provider from environment variables."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    # Fallback: check LLM_PROVIDER env var
    return os.environ.get("LLM_PROVIDER", "")


def _get_judge_model(provider):
    """Get a fast, cheap model for judging."""
    defaults = {
        "anthropic": "claude-haiku-4-5-20251001",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-1.5-flash",
    }
    return os.environ.get("JUDGE_MODEL", defaults.get(provider, ""))


def _call_llm(provider, model, system_prompt, user_prompt):
    """Call the LLM and return the response text."""
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model, max_tokens=500, temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    elif provider == "openai":
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model, max_tokens=500, temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    elif provider == "gemini":
        import google.generativeai as genai
        api_key = os.environ.get("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config={"temperature": 0, "max_output_tokens": 500},
        )
        return response.text

    else:
        print(f"ERROR: Unsupported provider '{provider}'", file=sys.stderr)
        sys.exit(1)


def run_judge(target_file, metric_name, rubric="", criteria=None):
    """Run the LLM judge on a target file and print the score."""
    if criteria is None:
        criteria = ["clarity", "accuracy", "completeness", "usefulness"]

    provider = _detect_provider()
    if not provider:
        print(f"ERROR: No LLM API key found in environment", file=sys.stderr)
        print(f"{metric_name}:0.0")
        sys.exit(1)

    model = _get_judge_model(provider)

    # Read target file
    try:
        with open(target_file) as f:
            content = f.read()
    except FileNotFoundError:
        # Try common fallback names
        for name in ["system_prompt.txt", "target.txt", "prompt.txt"]:
            try:
                with open(name) as f:
                    content = f.read()
                break
            except FileNotFoundError:
                continue
        else:
            print(f"ERROR: Target file '{target_file}' not found", file=sys.stderr)
            print(f"{metric_name}:0.0")
            sys.exit(1)

    criteria_text = "\n".join(f"- {c}" for c in criteria)
    rubric_text = f"\n\nRubric: {rubric}" if rubric else ""

    system_prompt = f"""You are an expert evaluator. Score the following content on these criteria (each 0-100):
{criteria_text}{rubric_text}

Return ONLY a JSON object with a score for each criterion. Example:
{json.dumps({c: 75 for c in criteria})}"""

    user_prompt = f"""Content to evaluate:

{content}

Return your scores as JSON only. No explanation."""

    try:
        text = _call_llm(provider, model, system_prompt, user_prompt)

        # Strip markdown fencing
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        scores = json.loads(text)

        # Average all scores
        values = [float(v) for v in scores.values() if isinstance(v, (int, float))]
        final_score = sum(values) / len(values) if values else 0.0

        print(f"{metric_name}:{final_score:.1f}")

    except json.JSONDecodeError:
        # If JSON parse fails, try to extract a single number
        import re
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
        if numbers:
            print(f"{metric_name}:{float(numbers[0]):.1f}")
        else:
            print(f"ERROR: Could not parse judge response: {text[:200]}", file=sys.stderr)
            print(f"{metric_name}:0.0")
    except Exception as e:
        print(f"ERROR: LLM judge failed: {e}", file=sys.stderr)
        print(f"{metric_name}:0.0")


if __name__ == "__main__":
    # Read config from eval_config.json if it exists, otherwise use env/defaults
    config = {}
    if os.path.exists("eval_config.json"):
        with open("eval_config.json") as f:
            config = json.load(f)

    target = os.environ.get("TARGET_FILE", config.get("target_file", "system_prompt.txt"))
    metric = config.get("metric_name", "quality_score")
    rubric = config.get("rubric", "")
    criteria = config.get("criteria", None)
    if isinstance(criteria, str):
        criteria = [c.strip() for c in criteria.split(",")]

    run_judge(target, metric, rubric, criteria)
