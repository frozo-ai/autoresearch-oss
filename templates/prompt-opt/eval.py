#!/usr/bin/env python3
"""Eval: Run prompt against labeled test cases. Provider-agnostic.

Works with Anthropic, OpenAI, and Gemini — auto-detects from environment.
Edit test_cases.json with your labeled examples.

Format: [{"input": "...", "expected": "..."}, ...]
"""

import json
import os
import sys

# Add autoresearch-oss to path for the reusable eval scripts
sys.path.insert(0, os.environ.get("PYTHONPATH", os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from evals.scripts.test_cases_eval import run_test_cases
    run_test_cases(
        prompt_file=os.environ.get("TARGET_FILE", "system_prompt.txt"),
        test_cases_file="test_cases.json",
        metric_name="accuracy_pct",
        match_mode="contains",
    )
except ImportError:
    # Fallback: inline provider-agnostic eval
    def _detect_provider():
        if os.environ.get("ANTHROPIC_API_KEY"): return "anthropic"
        if os.environ.get("OPENAI_API_KEY"): return "openai"
        if os.environ.get("GOOGLE_API_KEY"): return "gemini"
        return os.environ.get("LLM_PROVIDER", "")

    def _call_llm(provider, model, system_prompt, user_input):
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic()
            r = client.messages.create(model=model, max_tokens=100, temperature=0,
                system=system_prompt, messages=[{"role": "user", "content": user_input}])
            return r.content[0].text.strip()
        elif provider == "openai":
            import openai
            client = openai.OpenAI()
            r = client.chat.completions.create(model=model, max_tokens=100, temperature=0,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}])
            return r.choices[0].message.content.strip()
        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
            m = genai.GenerativeModel(model)
            r = m.generate_content(f"{system_prompt}\n\nUser: {user_input}", generation_config={"temperature": 0})
            return r.text.strip()
        else:
            print(f"ERROR: No API key found", file=sys.stderr); sys.exit(1)

    provider = _detect_provider()
    models = {"anthropic": "claude-haiku-4-5-20251001", "openai": "gpt-4o-mini", "gemini": "gemini-1.5-flash"}
    model = os.environ.get("LLM_MODEL", models.get(provider, ""))

    with open("system_prompt.txt") as f: prompt = f.read()
    with open("test_cases.json") as f: cases = json.load(f)

    correct, total = 0, len(cases)
    for i, c in enumerate(cases):
        out = _call_llm(provider, model, prompt, c["input"])
        exp = c.get("expected", c.get("expected_output", "")).strip().lower()
        match = exp in out.strip().lower()
        if match: correct += 1
        print(f"  Case {i+1}/{total}: {'PASS' if match else 'FAIL'} expected={exp[:40]} got={out[:40]}", file=sys.stderr)

    print(f"accuracy_pct:{correct/total*100:.1f}" if total else "accuracy_pct:0.0")
