"""Tests for results.tsv logging."""

import tempfile
from pathlib import Path

from runner.results import ExperimentResult, ResultsLog


def test_results_log_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = ResultsLog(Path(tmpdir) / "results.tsv")
        assert log.total_count == 0
        assert log.kept_count == 0
        assert log.best_result is None


def test_results_log_append():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = ResultsLog(Path(tmpdir) / "results.tsv")

        result = ExperimentResult(
            experiment_number=1,
            description="Added chain-of-thought",
            score=74.6,
            baseline_score=62.0,
            delta=12.6,
            kept=True,
            duration_seconds=45,
            commit_hash="abc1234",
        )
        log.append(result)

        assert log.total_count == 1
        assert log.kept_count == 1
        assert log.best_result is not None
        assert log.best_result.score == 74.6


def test_results_log_best_is_highest_kept():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = ResultsLog(Path(tmpdir) / "results.tsv")

        log.append(ExperimentResult(1, "First", 70.0, 62.0, 8.0, True, 30, "aaa"))
        log.append(ExperimentResult(2, "Second", 65.0, 62.0, 3.0, False, 25, "bbb"))
        log.append(ExperimentResult(3, "Third", 75.0, 62.0, 13.0, True, 40, "ccc"))

        assert log.best_result.score == 75.0
        assert log.best_result.experiment_number == 3
        assert log.kept_count == 2
        assert log.total_count == 3


def test_results_tsv_file_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "results.tsv"
        log = ResultsLog(path)
        log.append(ExperimentResult(1, "Test", 80.0, 60.0, 20.0, True, 10, "xyz"))

        content = path.read_text()
        lines = content.strip().splitlines()
        assert len(lines) == 2  # header + 1 row
        assert "experiment_number" in lines[0]
        assert "80.0000" in lines[1]


def test_results_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = ResultsLog(Path(tmpdir) / "results.tsv")
        log.append(ExperimentResult(1, "First", 74.6, 62.0, 12.6, True, 30, "abc"))
        log.append(ExperimentResult(2, "Second", 60.0, 62.0, -2.0, False, 20, "def"))

        summary = log.summary()
        assert "2 experiments" in summary
        assert "1 improvements" in summary
