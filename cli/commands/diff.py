"""ars diff — show what changed in the best version."""

import subprocess
from pathlib import Path

import click


def _git(args: list[str], cwd: Path) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _get_initial_commit(cwd: Path) -> str | None:
    return _git(["rev-list", "--max-parents=0", "HEAD"], cwd)


def _get_target_file(cwd: Path) -> str | None:
    """Try to determine the target file from program.md or common names."""
    program_path = cwd / "program.md"
    if program_path.exists():
        for line in program_path.read_text().splitlines():
            if "target_file" in line.lower() or "target file" in line.lower():
                for word in line.split():
                    if "." in word and not word.startswith("#"):
                        clean = word.strip("`\"',:;")
                        if (cwd / clean).exists() or len(clean) < 50:
                            return clean
    for name in ["system_prompt.txt", "prompt.txt", "config.yaml", "copy.txt", "solution.py", "target.txt"]:
        if (cwd / name).exists():
            return name
    return None


@click.command("diff")
@click.option("--raw", is_flag=True, help="Show raw git diff format")
@click.option("--copy", "do_copy", is_flag=True, help="Copy improved version to clipboard")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def diff_cmd(raw: bool, do_copy: bool, as_json: bool):
    """Show what changed in the best version.

    Displays a human-readable before/after comparison of the target file.
    Use --raw for git diff format, --copy to copy the improved version.
    """
    workspace = Path(".")

    initial = _get_initial_commit(workspace)
    if not initial:
        click.echo("No run results found. Run 'ars run' first.")
        return

    if raw:
        diff_output = _git(["diff", initial, "HEAD"], workspace)
        if diff_output:
            click.echo(diff_output)
        else:
            click.echo("No changes from baseline.")
        return

    target = _get_target_file(workspace)
    if not target:
        click.echo("Could not determine target file. Showing raw diff:")
        diff_output = _git(["diff", initial, "HEAD"], workspace)
        click.echo(diff_output or "No changes.")
        return

    before = _git(["show", f"{initial}:{target}"], workspace)
    after = _git(["show", f"HEAD:{target}"], workspace)

    if before is None or after is None:
        click.echo("Could not read file versions.")
        return

    # Read results for score info
    baseline_score = None
    best_score = None
    kept_descriptions: list[str] = []

    results_path = workspace / "results.tsv"
    if results_path.exists():
        lines = results_path.read_text().strip().splitlines()
        data_lines = lines[1:] if lines and lines[0].split("\t")[0] == "experiment_number" else lines
        for line in data_lines:
            parts = line.split("\t")
            if len(parts) > 5:
                try:
                    if baseline_score is None and len(parts) > 3:
                        baseline_score = float(parts[3])
                    score = float(parts[2])
                    if parts[5] == "True":
                        kept_descriptions.append(parts[1] if len(parts) > 1 else "")
                        if best_score is None or score > best_score:
                            best_score = score
                except (ValueError, IndexError):
                    pass

    if as_json:
        import json as json_mod
        output = {
            "target_file": target,
            "before": before,
            "after": after,
            "changed": before != after,
            "baseline_score": baseline_score,
            "best_score": best_score,
            "improvements_kept": len(kept_descriptions),
            "descriptions": kept_descriptions,
        }
        click.echo(json_mod.dumps(output, indent=2))
        return

    if before == after:
        click.echo("No improvements were made — the baseline was not beaten.")
        return

    # Display
    if baseline_score is not None and best_score is not None:
        improvement = (best_score - baseline_score) / baseline_score * 100 if baseline_score else 0
        click.echo(f"\nImproved: {baseline_score:.1f} → {best_score:.1f} ({improvement:+.1f}%)\n")
    else:
        click.echo("\nChanges from baseline:\n")

    click.echo(click.style("BEFORE:", fg="red", bold=True))
    for line in before.splitlines():
        click.echo(f"  {line}")

    click.echo()
    click.echo(click.style("AFTER:", fg="green", bold=True))
    for line in after.splitlines():
        click.echo(f"  {line}")

    if kept_descriptions:
        click.echo(f"\nChanges ({len(kept_descriptions)} improvement{'s' if len(kept_descriptions) != 1 else ''} kept):")
        for i, desc in enumerate(kept_descriptions, 1):
            click.echo(f"  {i}. {desc[:80]}")

    if do_copy:
        try:
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(after.encode())
            click.echo("\n  Copied improved version to clipboard.")
        except (FileNotFoundError, OSError):
            click.echo(f"\n  (Clipboard not available — copy the AFTER text manually)")

    click.echo("\n  ars apply  — write the improved version to your file")
