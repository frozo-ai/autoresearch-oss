"""ars apply — apply the best version from the experiment loop to the target file."""

import shutil
import subprocess
from pathlib import Path

import click


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _detect_target_file(workspace: Path) -> str | None:
    """Detect the target file from program.md."""
    program_path = workspace / "program.md"
    if not program_path.exists():
        return None

    content = program_path.read_text()
    for line in content.splitlines():
        line_lower = line.lower().strip()

        # Look for target_file or target file references
        if "target_file" in line_lower or "target file" in line_lower:
            # Parse "target_file: foo.txt" or "**Target file**: foo.txt" patterns
            for sep in [":", "=", "`"]:
                if sep in line:
                    candidate = line.split(sep)[-1].strip().strip("`").strip("*").strip()
                    if candidate and not candidate.startswith("#"):
                        return candidate

    # Fallback: check common target file names
    for name in ["system_prompt.txt", "prompt.txt", "config.yaml", "copy.txt",
                  "landing_copy.txt", "solution.py", "sop.md", "target.txt"]:
        if (workspace / name).exists():
            return name

    return None


def _parse_results_summary(workspace: Path) -> tuple[float, float]:
    """Parse results.tsv to get baseline and best score.

    Returns (baseline, best_score).
    """
    results_path = workspace / "results.tsv"
    if not results_path.exists():
        return 0.0, 0.0

    lines = results_path.read_text().strip().splitlines()
    if not lines:
        return 0.0, 0.0

    # Skip header
    first_fields = lines[0].split("\t")
    if first_fields and not first_fields[0].replace(".", "").replace("-", "").isdigit():
        data_lines = lines[1:]
    else:
        data_lines = lines

    if not data_lines:
        return 0.0, 0.0

    rows = [line.split("\t") for line in data_lines if line.strip()]

    baseline = 0.0
    best_score = 0.0
    try:
        baseline = float(rows[0][3])
    except (ValueError, IndexError):
        pass

    for r in rows:
        try:
            score = float(r[2])
            if score > best_score:
                best_score = score
        except (ValueError, IndexError):
            pass

    return baseline, best_score


@click.command("apply")
@click.option("--target-file", "-f", default=None, help="Target file to apply best version to")
@click.option("--branch", "-b", default="autoresearch/best", help="Git branch with the best version")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def apply_cmd(target_file: str | None, branch: str, yes: bool):
    """Apply the best version from the experiment loop to the target file.

    Reads the best version from the autoresearch/best git branch,
    shows a before/after comparison, and writes it to the target file
    after confirmation.
    """
    workspace = Path(".").resolve()

    # --- Resolve target file ---
    if not target_file:
        target_file = _detect_target_file(workspace)

    if not target_file:
        click.echo(
            "Could not detect target file. "
            "Use --target-file or ensure program.md specifies one.",
            err=True,
        )
        raise SystemExit(1)

    target_path = workspace / target_file
    click.echo(f"Target file: {target_file}")

    # --- Verify git repo ---
    result = _git(["rev-parse", "--is-inside-work-tree"], workspace)
    if result.returncode != 0:
        click.echo("Not a git repository. Run 'ars run' first to generate results.", err=True)
        raise SystemExit(1)

    # --- Get the best version from the branch ---
    result = _git(["show", f"{branch}:{target_file}"], workspace)
    if result.returncode != 0:
        click.echo(
            f"Could not read '{target_file}' from branch '{branch}'.\n"
            f"Make sure 'ars run' has completed successfully.",
            err=True,
        )
        raise SystemExit(1)

    best_content = result.stdout

    # --- Get the original version (from initial commit) ---
    initial = _git(["rev-list", "--max-parents=0", "HEAD"], workspace)
    if initial.returncode == 0 and initial.stdout.strip():
        first_commit = initial.stdout.strip().splitlines()[0]
        original_result = _git(["show", f"{first_commit}:{target_file}"], workspace)
        original_content = original_result.stdout if original_result.returncode == 0 else ""
    else:
        # Fall back to current file content
        original_content = target_path.read_text() if target_path.exists() else ""

    # --- Get score improvement ---
    baseline, best_score = _parse_results_summary(workspace)

    # --- Display comparison ---
    click.echo()
    click.echo("=" * 60)
    click.echo("BEFORE (original)")
    click.echo("=" * 60)
    if original_content.strip():
        # Show first 30 lines if long
        lines = original_content.splitlines()
        for line in lines[:30]:
            click.echo(f"  {line}")
        if len(lines) > 30:
            click.echo(f"  ... ({len(lines) - 30} more lines)")
    else:
        click.echo("  (empty)")

    click.echo()
    click.echo("=" * 60)
    click.echo("AFTER (best version)")
    click.echo("=" * 60)
    if best_content.strip():
        lines = best_content.splitlines()
        for line in lines[:30]:
            click.echo(f"  {line}")
        if len(lines) > 30:
            click.echo(f"  ... ({len(lines) - 30} more lines)")
    else:
        click.echo("  (empty)")

    click.echo()

    # --- Score summary ---
    if baseline > 0:
        improvement = (best_score - baseline) / baseline * 100
        click.echo(f"Score: {baseline:.4f} -> {best_score:.4f} ({improvement:+.1f}%)")
    elif best_score > 0:
        click.echo(f"Best score: {best_score:.4f}")

    click.echo()

    # --- Confirm ---
    if not yes:
        if not click.confirm("Apply this change?", default=True):
            click.echo("Aborted.")
            return

    # --- Create backup ---
    if target_path.exists():
        backup_path = target_path.with_suffix(target_path.suffix + ".bak")
        shutil.copy2(target_path, backup_path)
        click.echo(f"Backup saved to {backup_path.name}")

    # --- Write best version ---
    target_path.write_text(best_content)
    click.echo(f"Applied best version to {target_file}")
