"""Comprehensive CLI regression tests.

Tests all CLI commands, --json output, session state, REPL,
and the core loop features (early stopping, eval cache, strategy).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Add parent dirs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.ars import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path):
    """Create a minimal project directory with program.md and eval."""
    program = tmp_path / "program.md"
    program.write_text("""# Test Project

## Goal
Test optimization.

## Setup
Nothing needed.

## Constraints
- DO NOT MODIFY: eval.sh

## Experiment Loop
1. Read target
2. Run: bash eval.sh
3. Read metric: score from stdout

## Metric
metric_name: score
higher_is_better: true
""")
    target = tmp_path / "target.txt"
    target.write_text("initial content")

    eval_sh = tmp_path / "eval.sh"
    eval_sh.write_text('#!/bin/bash\necho "score:75.0"')
    eval_sh.chmod(0o755)

    return tmp_path


# ============================================================
# 1. CLI Help & Version
# ============================================================

class TestCLIBasics:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AutoResearch" in result.output
        assert "Quick start" in result.output
        assert "Cloud" in result.output
        assert "Config" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output

    def test_init_help(self, runner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--template" in result.output

    def test_run_help(self, runner):
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--cloud" in result.output

    def test_results_help(self, runner):
        result = runner.invoke(cli, ["results", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--csv" in result.output

    def test_status_help(self, runner):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_diff_help(self, runner):
        result = runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--raw" in result.output

    def test_apply_help(self, runner):
        result = runner.invoke(cli, ["apply", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output
        assert "set" in result.output
        assert "get" in result.output

    def test_login_help(self, runner):
        result = runner.invoke(cli, ["login", "--help"])
        assert result.exit_code == 0
        assert "--email" in result.output

    def test_deploy_help(self, runner):
        result = runner.invoke(cli, ["deploy", "--help"])
        assert result.exit_code == 0

    def test_upgrade_help(self, runner):
        result = runner.invoke(cli, ["upgrade", "--help"])
        assert result.exit_code == 0


# ============================================================
# 2. Init Command
# ============================================================

class TestInitCommand:
    def test_init_with_template(self, runner, tmp_path):
        result = runner.invoke(cli, ["init", "--template", "prompt-opt", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Scaffolding" in result.output
        assert (tmp_path / "program.md").exists()
        assert (tmp_path / "eval.py").exists()
        assert (tmp_path / "system_prompt.txt").exists()

    def test_init_with_config_template(self, runner, tmp_path):
        result = runner.invoke(cli, ["init", "--template", "config-tune", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "config.yaml").exists()
        assert (tmp_path / "eval.sh").exists()

    def test_init_with_test_pass_template(self, runner, tmp_path):
        result = runner.invoke(cli, ["init", "--template", "test-pass", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "solution.py").exists()
        assert (tmp_path / "test_solution.py").exists()

    def test_init_skip_existing_files(self, runner, tmp_path):
        # Create a file first
        (tmp_path / "program.md").write_text("existing")
        result = runner.invoke(cli, ["init", "--template", "prompt-opt", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Skipping program.md" in result.output
        # Original content preserved
        assert (tmp_path / "program.md").read_text() == "existing"

    def test_init_all_templates_exist(self):
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        for t in ["prompt-opt", "config-tune", "copy-opt", "test-pass", "sop"]:
            assert (templates_dir / t).exists(), f"Template {t} missing"
            assert (templates_dir / t / "program.md").exists(), f"Template {t} missing program.md"


# ============================================================
# 3. Status Command with --json
# ============================================================

class TestStatusCommand:
    def test_status_no_results(self, runner, tmp_path):
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["status"])
            assert "No results found" in result.output
        finally:
            os.chdir(old_cwd)

    def test_status_with_results(self, runner, tmp_path):
        results_file = tmp_path / "results.tsv"
        results_file.write_text(
            "experiment_number\tdescription\tscore\tbaseline_score\tdelta\tkept\tduration_seconds\tcommit_hash\tcrashed\tcrash_message\n"
            "1\ttest change\t0.8000\t0.7000\t+0.1000\tTrue\t3\tabc123\tFalse\t\n"
            "2\tbad change\t0.6500\t0.7000\t-0.0500\tFalse\t2\tdef456\tFalse\t\n"
        )
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "Experiments: 2" in result.output
            assert "Kept:        1" in result.output
        finally:
            os.chdir(old_cwd)

    def test_status_json_output(self, runner, tmp_path):
        results_file = tmp_path / "results.tsv"
        results_file.write_text(
            "experiment_number\tdescription\tscore\tbaseline_score\tdelta\tkept\tduration_seconds\tcommit_hash\tcrashed\tcrash_message\n"
            "1\ttest change\t0.8000\t0.7000\t+0.1000\tTrue\t3\tabc123\tFalse\t\n"
        )
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["experiments"] == 1
            assert data["kept"] == 1
            assert data["best_score"] == 0.8
            assert "last_experiments" in data
        finally:
            os.chdir(old_cwd)


# ============================================================
# 4. Results Command
# ============================================================

class TestResultsCommand:
    def test_results_no_file(self, runner, tmp_path):
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["results"])
            assert result.exit_code != 0 or "No results found" in result.output
        finally:
            os.chdir(old_cwd)

    def test_results_json_output(self, runner, tmp_path):
        results_file = tmp_path / "results.tsv"
        results_file.write_text(
            "experiment_number\tdescription\tscore\tbaseline_score\tdelta\tkept\tduration_seconds\tcommit_hash\tcrashed\tcrash_message\n"
            "1\ttest\t0.80\t0.70\t+0.10\tTrue\t3\tabc\tFalse\t\n"
        )
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["results", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "summary" in data
            assert "experiments" in data
        finally:
            os.chdir(old_cwd)

    def test_results_csv_output(self, runner, tmp_path):
        results_file = tmp_path / "results.tsv"
        results_file.write_text(
            "experiment_number\tdescription\tscore\tbaseline_score\tdelta\tkept\tduration_seconds\tcommit_hash\tcrashed\tcrash_message\n"
            "1\ttest\t0.80\t0.70\t+0.10\tTrue\t3\tabc\tFalse\t\n"
        )
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["results", "--csv"])
            assert result.exit_code == 0
            assert "Score" in result.output
            assert "0.80" in result.output
        finally:
            os.chdir(old_cwd)

    def test_results_table_output(self, runner, tmp_path):
        results_file = tmp_path / "results.tsv"
        results_file.write_text(
            "experiment_number\tdescription\tscore\tbaseline_score\tdelta\tkept\tduration_seconds\tcommit_hash\tcrashed\tcrash_message\n"
            "1\ttest desc\t0.80\t0.70\t+0.10\tTrue\t3\tabc\tFalse\t\n"
            "2\tbad desc\t0.65\t0.70\t-0.05\tFalse\t2\tdef\tFalse\t\n"
        )
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(cli, ["results"])
            assert result.exit_code == 0
            assert "Summary" in result.output
            assert "Baseline" in result.output
            assert "Best Score" in result.output
        finally:
            os.chdir(old_cwd)


# ============================================================
# 5. Config Command
# ============================================================

class TestConfigCommand:
    def test_config_show(self, runner):
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "Configuration" in result.output
        assert "API Keys" in result.output
        assert "Auth" in result.output
        assert "Session" in result.output

    def test_config_set_and_get(self, runner):
        result = runner.invoke(cli, ["config", "set", "provider", "openai"])
        assert result.exit_code == 0
        assert "Set provider = openai" in result.output

        result = runner.invoke(cli, ["config", "get", "provider"])
        assert result.exit_code == 0
        assert "openai" in result.output

    def test_config_set_invalid_key(self, runner):
        result = runner.invoke(cli, ["config", "set", "invalid_key", "value"])
        assert result.exit_code != 0


# ============================================================
# 6. Session State
# ============================================================

class TestSessionState:
    def test_session_save_and_load(self):
        from cli.session import save_session, load_session
        save_session({"test_key": "test_value"})
        session = load_session()
        assert session["test_key"] == "test_value"
        assert "updated_at" in session

    def test_session_update_after_run(self):
        from cli.session import update_after_run, load_session
        update_after_run(
            workspace="/tmp/test",
            provider="anthropic",
            model="claude-haiku-4-5",
            max_experiments=50,
            total=50,
            kept=12,
            best_score=0.85,
            baseline=0.70,
        )
        session = load_session()
        assert session["last_provider"] == "anthropic"
        assert session["last_model"] == "claude-haiku-4-5"
        assert session["last_run"]["total_experiments"] == 50

    def test_session_get_last_provider(self):
        from cli.session import save_session, get_last_provider
        save_session({"last_provider": "gemini"})
        assert get_last_provider() == "gemini"

    def test_session_get_last_model(self):
        from cli.session import save_session, get_last_model
        save_session({"last_model": "gpt-4o"})
        assert get_last_model() == "gpt-4o"


# ============================================================
# 7. Core Loop Features (already tested, verify still passing)
# ============================================================

class TestLoopFeatures:
    def test_cancel_flag_no_redis(self):
        from runner.loop import _check_cancel_flag
        assert _check_cancel_flag("test") is False

    def test_cancel_flag_with_redis(self):
        from runner.loop import _check_cancel_flag
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"1"
        with patch("runner.loop._get_redis_client", return_value=mock_redis):
            assert _check_cancel_flag("test") is True

    def test_stagnation_detected(self):
        from runner.loop import _check_stagnation
        assert _check_stagnation([False] * 15, window=15) is True

    def test_stagnation_not_detected(self):
        from runner.loop import _check_stagnation
        assert _check_stagnation([False] * 14 + [True], window=15) is False
        assert _check_stagnation([False] * 10, window=15) is False

    def test_eval_cache(self):
        from runner.loop import EvalCache
        cache = EvalCache()
        assert cache.lookup("test") is None
        cache.record("test", 85.0, False, 1)
        assert cache.lookup("test") == (85.0, False, 1)
        assert cache.lookup("other") is None

    def test_strategy_starts_explore(self):
        from runner.strategy import LoopStrategy
        s = LoopStrategy()
        assert s.get_mode() == "explore"
        assert s.get_temperature() == 1.0

    def test_strategy_switches_to_exploit(self):
        from runner.strategy import LoopStrategy
        s = LoopStrategy()
        for _ in range(8):
            s.record(kept=False)
        s.record(kept=True)
        s.record(kept=True)
        assert s.get_mode() == "exploit"
        assert s.get_temperature() == 0.3

    def test_strategy_override(self):
        from runner.strategy import LoopStrategy
        s = LoopStrategy(override="exploit_only")
        assert s.get_mode() == "exploit"
        s = LoopStrategy(override="explore_only")
        s.record(kept=True)
        s.record(kept=True)
        assert s.get_mode() == "explore"


# ============================================================
# 8. Cost Estimation
# ============================================================

class TestCostEstimation:
    def test_estimate_returns_range(self):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "api"))
        from services.cost_service import estimate_run_cost
        result = estimate_run_cost("anthropic", "claude-haiku-4-5-20251001", "x" * 2000, "goal", 100)
        assert result["estimated_low_usd"] > 0
        assert result["estimated_high_usd"] > result["estimated_low_usd"]
        assert result["per_experiment_tokens"] > 0

    def test_estimate_scales_linearly(self):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "api"))
        from services.cost_service import estimate_run_cost
        c50 = estimate_run_cost("anthropic", "claude-haiku-4-5-20251001", "x" * 2000, "g", 50)
        c100 = estimate_run_cost("anthropic", "claude-haiku-4-5-20251001", "x" * 2000, "g", 100)
        ratio = c100["estimated_low_usd"] / c50["estimated_low_usd"]
        assert 1.8 < ratio < 2.2


# ============================================================
# 9. Memory Task
# ============================================================

class TestMemoryTask:
    def test_build_memory(self):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "worker"))
        from tasks.memory_task import build_memory_from_experiments
        experiments = [
            {"description": "Add CoT", "score": 72.0, "baseline_score": 62.0, "delta": 10.0, "kept": True, "crashed": False},
            {"description": "Remove all", "score": 55.0, "baseline_score": 62.0, "delta": -7.0, "kept": False, "crashed": False},
        ]
        memory = build_memory_from_experiments(experiments, "test-1", None)
        assert memory["total_runs"] == 1
        assert memory["total_experiments"] == 2
        assert len(memory["strategies_that_worked"]) == 1

    def test_format_memory_context(self):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "worker"))
        from tasks.memory_task import format_memory_context
        assert format_memory_context(None) == ""
        assert format_memory_context({"total_runs": 0}) == ""
        memory = {
            "total_runs": 1, "total_experiments": 50,
            "strategies_that_worked": [{"description": "CoT", "delta": 8.0, "run_tag": "t1"}],
            "strategies_that_failed": [],
        }
        result = format_memory_context(memory)
        assert "CoT" in result
        assert "1 previous runs" in result


# ============================================================
# 10. Template Eval Scripts are Provider-Agnostic
# ============================================================

class TestTemplateEvals:
    """Verify template eval scripts don't hardcode 'from openai import OpenAI'."""

    def test_prompt_opt_eval_is_agnostic(self):
        eval_path = Path(__file__).parent.parent.parent / "templates" / "prompt-opt" / "eval.py"
        content = eval_path.read_text()
        assert "from openai import OpenAI" not in content
        assert "_detect_provider" in content or "evals.scripts" in content

    def test_copy_opt_eval_is_agnostic(self):
        eval_path = Path(__file__).parent.parent.parent / "templates" / "copy-opt" / "eval.py"
        content = eval_path.read_text()
        assert "from openai import OpenAI" not in content

    def test_sop_eval_is_agnostic(self):
        eval_path = Path(__file__).parent.parent.parent / "templates" / "sop" / "eval.py"
        content = eval_path.read_text()
        assert "from openai import OpenAI" not in content

    def test_test_pass_eval_is_bash(self):
        eval_path = Path(__file__).parent.parent.parent / "templates" / "test-pass" / "eval.sh"
        content = eval_path.read_text()
        assert "pytest" in content or "pass_pct" in content

    def test_config_tune_eval_is_bash(self):
        eval_path = Path(__file__).parent.parent.parent / "templates" / "config-tune" / "eval.sh"
        content = eval_path.read_text()
        assert "benchmark_score" in content or "score" in content


# ============================================================
# 11. SKILL.md Exists and Is Valid
# ============================================================

class TestSkillMd:
    def test_skill_md_exists(self):
        skill_path = Path(__file__).parent.parent / "skills" / "SKILL.md"
        assert skill_path.exists(), "SKILL.md not found"

    def test_skill_md_has_frontmatter(self):
        skill_path = Path(__file__).parent.parent / "skills" / "SKILL.md"
        content = skill_path.read_text()
        assert content.startswith("---")
        assert "name: autoresearch" in content
        assert "version: 0.2.0" in content
        assert "binary: ars" in content

    def test_skill_md_lists_all_commands(self):
        skill_path = Path(__file__).parent.parent / "skills" / "SKILL.md"
        content = skill_path.read_text()
        for cmd in ["init", "run", "results", "status", "diff", "apply", "config", "login", "deploy", "upgrade"]:
            assert f"name: {cmd}" in content, f"Command '{cmd}' not in SKILL.md"


# ============================================================
# 12. REPL Module Loads
# ============================================================

class TestREPL:
    def test_repl_module_imports(self):
        from cli.repl import start_repl, BANNER, QUICK_HELP
        assert "AutoResearch" in BANNER
        assert "init" in QUICK_HELP
        assert "run" in QUICK_HELP
        assert "quit" in QUICK_HELP

    def test_repl_invoked_when_no_command(self, runner):
        """REPL is invoked when no subcommand given -- but we can't test interactive input.
        Instead verify the group is configured for invoke_without_command."""
        assert cli.invoke_without_command is True


# ============================================================
# 13. Subprocess Integration Tests
# ============================================================

class TestSubprocessIntegration:
    """Run CLI via subprocess to verify end-to-end behavior."""

    _base_cmd = [sys.executable, "-m", "cli.ars"]
    _cwd = str(Path(__file__).parent.parent.parent)

    def test_help_via_subprocess(self):
        result = subprocess.run(
            self._base_cmd + ["--help"],
            cwd=self._cwd, capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "AutoResearch" in result.stdout

    def test_version_via_subprocess(self):
        result = subprocess.run(
            self._base_cmd + ["--version"],
            cwd=self._cwd, capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "0.2.0" in result.stdout

    def test_init_via_subprocess(self, tmp_path):
        result = subprocess.run(
            self._base_cmd + ["init", "--template", "prompt-opt", "--dir", str(tmp_path)],
            cwd=self._cwd, capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert (tmp_path / "program.md").exists()

    def test_status_no_results_via_subprocess(self, tmp_path):
        result = subprocess.run(
            self._base_cmd + ["status"],
            cwd=str(tmp_path), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": self._cwd},
        )
        assert result.returncode == 0
        assert "No results found" in result.stdout

    def test_config_show_via_subprocess(self):
        result = subprocess.run(
            self._base_cmd + ["config", "show"],
            cwd=self._cwd, capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Configuration" in result.stdout
