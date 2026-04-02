"""Git ratchet — branch management and keep/revert logic.

The ratchet pattern:
1. Create experiment branch from current best
2. Apply proposed changes
3. Run eval
4. If improved: merge to best branch (keep)
5. If not improved: discard experiment branch (revert)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitRatchet:
    """Manages git branches for the experiment ratchet loop."""

    def __init__(self, repo_path: str | Path = "."):
        self.repo_path = Path(repo_path)
        self.best_branch = "autoresearch/best"
        self._ensure_git_repo()

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the repo directory."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result

    def _ensure_git_repo(self) -> None:
        """Ensure the working directory is a git repo."""
        result = self._run("rev-parse", "--is-inside-work-tree", check=False)
        if result.returncode != 0:
            logger.info("Initializing git repo at %s", self.repo_path)
            self._run("init")
            self._run("config", "user.email", "runner@autoresearch.local")
            self._run("config", "user.name", "AutoResearch Runner")
            # Exclude results.tsv and run.log from git — they must survive reverts
            gitignore = self.repo_path / ".gitignore"
            gitignore.write_text("results.tsv\nrun.log\n*.log\n*.txt.bak\n__pycache__/\n*.pyc\n.DS_Store\n")
            self._run("add", ".")
            self._run("commit", "-m", "Initial commit (autoresearch baseline)")

    def setup_best_branch(self) -> None:
        """Create the best branch from current HEAD if it doesn't exist."""
        result = self._run("branch", "--list", self.best_branch, check=False)
        if not result.stdout.strip():
            self._run("checkout", "-b", self.best_branch)
            logger.info("Created best branch: %s", self.best_branch)
        else:
            self._run("checkout", self.best_branch)

    def create_experiment_branch(self, experiment_number: int) -> str:
        """Create a new experiment branch from the best branch."""
        branch_name = f"autoresearch/exp-{experiment_number:04d}"
        self._run("checkout", self.best_branch)
        self._run("checkout", "-b", branch_name)
        logger.info("Created experiment branch: %s", branch_name)
        return branch_name

    def commit_changes(self, message: str) -> str:
        """Stage and commit all changes, return the commit hash."""
        self._run("add", ".")
        result = self._run("commit", "-m", message, check=False)
        if result.returncode != 0:
            # No changes to commit
            return self.get_current_hash()
        return self.get_current_hash()

    def get_current_hash(self) -> str:
        """Get the current commit hash (short)."""
        result = self._run("rev-parse", "--short", "HEAD")
        return result.stdout.strip()

    def keep(self, experiment_branch: str) -> None:
        """Merge experiment branch into best (ratchet forward)."""
        self._run("checkout", self.best_branch)
        self._run("merge", experiment_branch, "--no-edit")
        self._run("branch", "-d", experiment_branch)
        logger.info("Kept: merged %s into %s", experiment_branch, self.best_branch)

    def revert(self, experiment_branch: str) -> None:
        """Discard experiment branch (ratchet stays)."""
        self._run("checkout", self.best_branch)
        self._run("branch", "-D", experiment_branch)
        logger.info("Reverted: discarded %s", experiment_branch)

    def get_best_diff(self) -> str:
        """Get the diff between initial commit and current best."""
        # Find the initial commit
        result = self._run("rev-list", "--max-parents=0", "HEAD")
        initial_commit = result.stdout.strip().splitlines()[0]
        diff_result = self._run("diff", initial_commit, "HEAD")
        return diff_result.stdout

    def get_current_branch(self) -> str:
        result = self._run("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()
