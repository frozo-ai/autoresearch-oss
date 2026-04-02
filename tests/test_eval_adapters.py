"""Tests for eval adapters."""

import tempfile
from pathlib import Path

from evals.base import EvalResult
from evals.bash_script import BashScriptAdapter
from evals.python_script import PythonScriptAdapter
from evals import get_adapter


def test_get_adapter_python():
    adapter = get_adapter("python_script")
    assert isinstance(adapter, PythonScriptAdapter)


def test_get_adapter_bash():
    adapter = get_adapter("bash")
    assert isinstance(adapter, BashScriptAdapter)


def test_get_adapter_invalid():
    import pytest
    with pytest.raises(ValueError, match="Unknown eval type"):
        get_adapter("nonexistent")


def test_python_script_adapter_file_not_found():
    adapter = PythonScriptAdapter({"script_path": "nonexistent.py"})
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(Path(tmpdir), "accuracy")
    assert not result.success
    assert "not found" in result.error_message


def test_python_script_adapter_success():
    adapter = PythonScriptAdapter({"script_path": "eval.py"})
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        eval_script = workspace / "eval.py"
        eval_script.write_text('print("accuracy:85.5")')

        result = adapter.run(workspace, "accuracy")
    assert result.success
    assert result.score == 85.5
    assert result.metric_name == "accuracy"


def test_bash_script_adapter_success():
    adapter = BashScriptAdapter({"script_path": "eval.sh"})
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        eval_script = workspace / "eval.sh"
        eval_script.write_text('#!/bin/bash\necho "score:92.3"')
        eval_script.chmod(0o755)

        result = adapter.run(workspace, "score")
    assert result.success
    assert result.score == 92.3


def test_bash_script_adapter_missing_metric():
    adapter = BashScriptAdapter({"script_path": "eval.sh"})
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        eval_script = workspace / "eval.sh"
        eval_script.write_text('#!/bin/bash\necho "no metric here"')
        eval_script.chmod(0o755)

        result = adapter.run(workspace, "score")
    assert not result.success
    assert "not found" in result.error_message


def test_parse_metric_base():
    from evals.base import EvalAdapter

    class TestAdapter(EvalAdapter):
        def run(self, workspace, metric_name):
            return EvalResult(metric_name=metric_name, score=0, success=True)

    adapter = TestAdapter({})
    assert adapter._parse_metric("accuracy:85.5\nother:10", "accuracy") == 85.5
    assert adapter._parse_metric("no match here", "accuracy") is None
    assert adapter._parse_metric("accuracy:not_a_number", "accuracy") is None
