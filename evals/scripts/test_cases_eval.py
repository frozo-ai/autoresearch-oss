#!/usr/bin/env python3
"""Test-case-based eval — runs the prompt against labeled examples.

The most common eval: user provides test cases as JSON, eval runs the
prompt against each case and checks if the output matches expected.

Test cases file format (test_cases.json):
[
  {"input": "classify: urgent server down", "expected": "critical"},
  {"input": "classify: update docs typo", "expected": "low"},
  ...
]

Match modes:
  - exact: output must exactly equal expected (case-insensitive, stripped)
  - contains: expected must appear somewhere in output
  - starts_with: output must start with expected
  - llm_judge: use LLM to judge if output matches expected (fuzzy)

Works with Anthropic, OpenAI, and Gemini — auto-detects from environment.
Prints: accuracy_pct:XX.X to stdout.
"""

import json
import os
import re
import sys


def _detect_provider():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return os.environ.get("LLM_PROVIDER", "")


def _get_model(provider):
    defaults = {
        "anthropic": "claude-haiku-4-5-20251001",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-1.5-flash",
    }
    return os.environ.get("LLM_MODEL", defaults.get(provider, ""))


def _call_llm(provider, model, system_prompt, user_input):
    """Call the LLM with the system prompt being tested + user input."""
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model, max_tokens=1024, temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
        )
        return response.content[0].text.strip()

    elif provider == "openai":
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model, max_tokens=1024, temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        return response.choices[0].message.content.strip()

    elif provider == "gemini":
        import google.generativeai as genai
        api_key = os.environ.get("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(
            f"{system_prompt}\n\nUser: {user_input}",
            generation_config={"temperature": 0, "max_output_tokens": 1024},
        )
        return response.text.strip()

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def _check_match(output, expected, mode="contains"):
    """Check if output matches expected based on match mode."""
    output_clean = output.strip().lower()
    expected_clean = expected.strip().lower()

    if mode == "exact":
        return output_clean == expected_clean
    elif mode == "starts_with":
        return output_clean.startswith(expected_clean)
    elif mode == "contains":
        return expected_clean in output_clean
    else:
        return expected_clean in output_clean


def _check_match_llm_judge(output, expected, provider, model):
    """Use LLM to judge if output semantically matches expected."""
    judge_prompt = (
        "You are a strict evaluator. Does the ACTUAL output match the EXPECTED output "
        "in meaning? Reply with ONLY 'yes' or 'no'."
    )
    user_msg = f"EXPECTED: {expected}\nACTUAL: {output}"

    try:
        result = _call_llm(provider, model, judge_prompt, user_msg)
        return result.strip().lower().startswith("yes")
    except Exception:
        # Fallback to contains match
        return expected.strip().lower() in output.strip().lower()


def run_test_cases(
    prompt_file, test_cases_file, metric_name="accuracy_pct",
    match_mode="contains", max_cases=None,
):
    """Run prompt against test cases and report accuracy."""
    provider = _detect_provider()
    if not provider:
        print(f"ERROR: No LLM API key found in environment", file=sys.stderr)
        print(f"{metric_name}:0.0")
        sys.exit(1)

    model = _get_model(provider)

    # Read the prompt being optimized
    try:
        with open(prompt_file) as f:
            system_prompt = f.read()
    except FileNotFoundError:
        for name in ["system_prompt.txt", "target.txt", "prompt.txt"]:
            try:
                with open(name) as f:
                    system_prompt = f.read()
                break
            except FileNotFoundError:
                continue
        else:
            print(f"ERROR: Prompt file '{prompt_file}' not found", file=sys.stderr)
            print(f"{metric_name}:0.0")
            sys.exit(1)

    # Read test cases
    try:
        with open(test_cases_file) as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Test cases file '{test_cases_file}' not found", file=sys.stderr)
        print(f"{metric_name}:0.0")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in test cases: {e}", file=sys.stderr)
        print(f"{metric_name}:0.0")
        sys.exit(1)

    if max_cases:
        test_cases = test_cases[:max_cases]

    if not test_cases:
        print(f"ERROR: No test cases found", file=sys.stderr)
        print(f"{metric_name}:0.0")
        sys.exit(1)

    correct = 0
    total = len(test_cases)

    for i, case in enumerate(test_cases):
        input_text = case.get("input", "")
        expected = case.get("expected", case.get("expected_output", ""))

        if not input_text or not expected:
            print(f"  SKIP case {i+1}: missing input or expected", file=sys.stderr)
            total -= 1
            continue

        try:
            output = _call_llm(provider, model, system_prompt, input_text)

            if match_mode == "llm_judge":
                match = _check_match_llm_judge(output, expected, provider, model)
            else:
                match = _check_match(output, expected, match_mode)

            status = "PASS" if match else "FAIL"
            if match:
                correct += 1

            print(f"  Case {i+1}/{total}: {status} | expected='{expected[:50]}' got='{output[:50]}'",
                  file=sys.stderr)

        except Exception as e:
            print(f"  Case {i+1}/{total}: ERROR | {e}", file=sys.stderr)

    accuracy = (correct / total * 100) if total > 0 else 0.0
    print(f"{metric_name}:{accuracy:.1f}")


if __name__ == "__main__":
    config = {}
    if os.path.exists("eval_config.json"):
        with open("eval_config.json") as f:
            config = json.load(f)

    prompt_file = os.environ.get("TARGET_FILE", config.get("target_file", "system_prompt.txt"))
    test_cases_file = config.get("test_cases_file", "test_cases.json")
    metric = config.get("metric_name", "accuracy_pct")
    match_mode = config.get("match_mode", "contains")
    max_cases = config.get("max_cases", None)

    run_test_cases(prompt_file, test_cases_file, metric, match_mode, max_cases)
