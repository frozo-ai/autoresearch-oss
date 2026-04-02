"""TSV results logging for experiment runs.

Outputs results in the format:
experiment_number\tdescription\tscore\tbaseline_score\tdelta\tkept\tduration_seconds\tcommit_hash
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExperimentResult:
    """Single experiment result."""

    experiment_number: int
    description: str
    score: float
    baseline_score: float
    delta: float
    kept: bool
    duration_seconds: int
    commit_hash: str
    crashed: bool = False
    crash_message: str = ""
    cached: bool = False
    mode: str = ""


HEADERS = [
    "experiment_number",
    "description",
    "score",
    "baseline_score",
    "delta",
    "kept",
    "duration_seconds",
    "commit_hash",
    "crashed",
    "crash_message",
    "cached",
    "mode",
]


class ResultsLog:
    """Manages the results.tsv file for an experiment run."""

    def __init__(self, path: str | Path = "results.tsv"):
        self.path = Path(path)
        self.results: list[ExperimentResult] = []

        # Write header if file doesn't exist
        if not self.path.exists():
            self._write_header()

    def _write_header(self) -> None:
        with open(self.path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(HEADERS)

    def append(self, result: ExperimentResult) -> None:
        """Append an experiment result to the log."""
        self.results.append(result)
        with open(self.path, "a", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                result.experiment_number,
                result.description,
                f"{result.score:.4f}",
                f"{result.baseline_score:.4f}",
                f"{result.delta:+.4f}",
                result.kept,
                result.duration_seconds,
                result.commit_hash,
                result.crashed,
                result.crash_message,
                result.cached,
                result.mode,
            ])

    @property
    def best_result(self) -> ExperimentResult | None:
        """Return the best kept result."""
        kept = [r for r in self.results if r.kept and not r.crashed]
        if not kept:
            return None
        return max(kept, key=lambda r: r.score)

    @property
    def kept_count(self) -> int:
        return sum(1 for r in self.results if r.kept)

    @property
    def total_count(self) -> int:
        return len(self.results)

    def summary(self) -> str:
        """Return a human-readable summary."""
        best = self.best_result
        if not best:
            return f"{self.total_count} experiments, 0 improvements kept"
        baseline = self.results[0].baseline_score if self.results else 0
        improvement = best.score - baseline
        pct = (improvement / baseline * 100) if baseline != 0 else 0
        return (
            f"{self.total_count} experiments, {self.kept_count} improvements kept | "
            f"Best: {best.score:.2f} ({improvement:+.2f}, {pct:+.1f}%)"
        )

    def to_tsv_string(self) -> str:
        """Return the full results as a TSV string."""
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter="\t")
        writer.writerow(HEADERS)
        for r in self.results:
            writer.writerow([
                r.experiment_number,
                r.description,
                f"{r.score:.4f}",
                f"{r.baseline_score:.4f}",
                f"{r.delta:+.4f}",
                r.kept,
                r.duration_seconds,
                r.commit_hash,
                r.crashed,
                r.crash_message,
                r.cached,
                r.mode,
            ])
        return buf.getvalue()
