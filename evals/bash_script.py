"""Bash script eval adapter — runs a shell script and parses the metric from stdout."""

import logging
import subprocess
from pathlib import Path

from evals.base import EvalAdapter, EvalResult

logger = logging.getLogger(__name__)


class BashScriptAdapter(EvalAdapter):
    """Run a bash eval script.

    Config:
        script_path: Path to the shell eval script (relative to workspace)
        timeout_seconds: Override time budget (optional)
    """

    def run(self, workspace: Path, metric_name: str) -> EvalResult:
        script_path = self.config.get("script_path", "eval.sh")
        timeout = self.config.get("timeout_seconds", self.time_budget)

        full_path = workspace / script_path
        if not full_path.exists():
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Eval script not found: {script_path}",
            )

        try:
            result = subprocess.run(
                ["bash", str(full_path)],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Eval timed out after {timeout}s",
            )

        if result.returncode != 0:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Eval failed (exit {result.returncode}): {result.stderr[:500]}",
                raw_output=result.stdout,
            )

        score = self._parse_metric(result.stdout, metric_name)
        if score is None:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Metric '{metric_name}' not found in output",
                raw_output=result.stdout,
            )

        return EvalResult(
            metric_name=metric_name,
            score=score,
            success=True,
            raw_output=result.stdout,
        )
