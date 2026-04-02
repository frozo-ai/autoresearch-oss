"""Abstract base class for eval adapters.

All eval adapters must implement the `run` method which:
1. Accepts no arguments (all config via env vars or adapter config)
2. Returns an EvalResult with metric_name, score, and success flag
3. Completes within TIME_BUDGET seconds
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    """Result from running an eval adapter."""

    metric_name: str
    score: float
    success: bool
    error_message: str = ""
    raw_output: str = ""


class EvalAdapter(ABC):
    """Base class for all eval adapters."""

    def __init__(self, config: dict):
        self.config = config
        self.time_budget = int(os.environ.get("TIME_BUDGET", "300"))

    @abstractmethod
    def run(self, workspace: Path, metric_name: str) -> EvalResult:
        """Run the eval and return the result.

        Args:
            workspace: Path to the project workspace
            metric_name: Name of the metric to parse from output

        Returns:
            EvalResult with the score and metadata
        """
        ...

    def _parse_metric(self, output: str, metric_name: str) -> float | None:
        """Parse metric_name:value from output text."""
        for line in output.splitlines():
            line = line.strip()
            if line.startswith(f"{metric_name}:"):
                try:
                    return float(line.split(":", 1)[1].strip())
                except ValueError:
                    continue
        return None
