"""LLM-as-judge eval adapter — uses a secondary LLM to score output quality."""

import json
import logging
import os
from pathlib import Path

from evals.base import EvalAdapter, EvalResult

logger = logging.getLogger(__name__)

DEFAULT_CRITERIA = ["clarity", "accuracy", "completeness", "conciseness"]


class LLMJudgeAdapter(EvalAdapter):
    """Use an LLM to judge the quality of a target file.

    Config:
        criteria: List of scoring criteria (default: clarity, accuracy, completeness, conciseness)
        weights: Weights for each criterion (default: equal)
        judge_model: Model to use for judging (default: same as experiment model)
        judge_provider: Provider for judge (default: same as experiment provider)
        rubric: Optional rubric text for the judge
    """

    def run(self, workspace: Path, metric_name: str) -> EvalResult:
        criteria = self.config.get("criteria", DEFAULT_CRITERIA)
        weights = self.config.get("weights", [1.0] * len(criteria))
        judge_provider = self.config.get(
            "judge_provider", os.environ.get("LLM_PROVIDER", "anthropic")
        )
        judge_model = self.config.get(
            "judge_model", os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
        )
        rubric = self.config.get("rubric", "")

        # Find the target file to judge
        target_file = self.config.get("target_file")
        if not target_file:
            # Try common names
            for name in ["prompt.txt", "system_prompt.txt", "target.txt", "output.txt"]:
                if (workspace / name).exists():
                    target_file = name
                    break
        if not target_file:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message="No target file found for LLM judge",
            )

        content = (workspace / target_file).read_text()

        # Build judge prompt
        criteria_text = "\n".join(f"- {c}" for c in criteria)
        system_prompt = f"""You are an expert evaluator. Score the following content on these criteria (each 0-100):
{criteria_text}

{f"Rubric: {rubric}" if rubric else ""}

Return ONLY a JSON object with scores for each criterion. Example:
{{"clarity": 85, "accuracy": 72, "completeness": 90, "conciseness": 68}}"""

        user_prompt = f"""Content to evaluate:

{content}

Return your scores as JSON."""

        try:
            if judge_provider == "anthropic":
                import anthropic

                client = anthropic.Anthropic()
                response = client.messages.create(
                    model=judge_model,
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text = response.content[0].text
            elif judge_provider == "openai":
                import openai

                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model=judge_model,
                    max_tokens=500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                text = response.choices[0].message.content
            else:
                return EvalResult(
                    metric_name=metric_name,
                    score=0.0,
                    success=False,
                    error_message=f"LLM judge: unsupported provider {judge_provider}",
                )

            # Parse scores
            text = text.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            scores = json.loads(text)

            # Calculate weighted average
            total_weight = sum(weights[:len(criteria)])
            weighted_sum = sum(
                scores.get(c, 0) * w for c, w in zip(criteria, weights)
            )
            final_score = weighted_sum / total_weight if total_weight > 0 else 0

            return EvalResult(
                metric_name=metric_name,
                score=final_score,
                success=True,
                raw_output=json.dumps(scores, indent=2),
            )

        except json.JSONDecodeError as e:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Judge returned invalid JSON: {e}",
            )
        except Exception as e:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"LLM judge error: {e}",
            )
