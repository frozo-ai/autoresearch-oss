#!/usr/bin/env python3
"""Eval: LLM judge scores SOP document quality. Provider-agnostic.

Works with Anthropic, OpenAI, and Gemini — auto-detects from environment.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.environ.get("PYTHONPATH", os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from evals.scripts.llm_judge_eval import run_judge
    run_judge(
        target_file=os.environ.get("TARGET_FILE", "sop.md"),
        metric_name="sop_quality",
        rubric="Rate this SOP for incident response. Score on completeness, clarity, actionability, and safety/escalation paths. Be a tough grader.",
        criteria=["completeness", "clarity", "actionability", "safety_escalation"],
    )
except ImportError:
    # Fallback: inline provider-agnostic eval
    def _detect():
        if os.environ.get("ANTHROPIC_API_KEY"): return "anthropic"
        if os.environ.get("OPENAI_API_KEY"): return "openai"
        if os.environ.get("GOOGLE_API_KEY"): return "gemini"
        return os.environ.get("LLM_PROVIDER", "")

    def _call(provider, model, sys_p, user_p):
        if provider == "anthropic":
            import anthropic; c = anthropic.Anthropic()
            return c.messages.create(model=model, max_tokens=500, temperature=0, system=sys_p, messages=[{"role":"user","content":user_p}]).content[0].text
        elif provider == "openai":
            import openai; c = openai.OpenAI()
            return c.chat.completions.create(model=model, max_tokens=500, temperature=0, messages=[{"role":"system","content":sys_p},{"role":"user","content":user_p}]).choices[0].message.content
        elif provider == "gemini":
            import google.generativeai as genai; genai.configure(api_key=os.environ.get("GOOGLE_API_KEY",""))
            return genai.GenerativeModel(model).generate_content(f"{sys_p}\n\n{user_p}", generation_config={"temperature":0}).text
        print("ERROR: No API key", file=sys.stderr); sys.exit(1)

    prov = _detect()
    mdl = os.environ.get("LLM_MODEL", {"anthropic":"claude-haiku-4-5-20251001","openai":"gpt-4o-mini","gemini":"gemini-1.5-flash"}.get(prov,""))
    with open(os.environ.get("TARGET_FILE", "sop.md")) as f: sop = f.read()
    sys_p = "Score this SOP 0-100 on completeness, clarity, actionability, safety_escalation. Return JSON only: {\"completeness\":N,\"clarity\":N,\"actionability\":N,\"safety_escalation\":N}"
    text = _call(prov, mdl, sys_p, sop)
    m = re.search(r'\{[^}]+\}', text)
    if m:
        scores = json.loads(m.group()); total = sum(scores.values())
        print(f"sop_quality:{total}")
    else:
        print("sop_quality:50.0")
