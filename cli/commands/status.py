"""ars status — show status of most recent run."""

import json
import webbrowser
from pathlib import Path

import click

CONFIG_FILE = Path.home() / ".autoresearch" / "config.json"


@click.command("status")
@click.argument("run_id", required=False)
@click.option("--cloud", is_flag=True, help="Open run in cloud dashboard")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def status_cmd(run_id: str | None, cloud: bool, as_json: bool):
    """Show status of the most recent (or specified) run."""

    if cloud:
        _show_cloud_status(run_id)
        return

    results_path = Path("results.tsv")
    if not results_path.exists():
        click.echo("No results found. Run 'ars run' first.")
        return

    lines = results_path.read_text().strip().splitlines()

    # Detect header
    if lines and lines[0].split("\t")[0] == "experiment_number":
        data_lines = lines[1:]
    else:
        data_lines = lines

    if not data_lines:
        click.echo("No experiments completed yet.")
        return

    rows = [line.split("\t") for line in data_lines if line.strip()]

    total = len(rows)
    kept = sum(1 for r in rows if len(r) > 5 and r[5] == "True")
    crashed = sum(1 for r in rows if len(r) > 8 and r[8] == "True")

    scores = []
    for r in rows:
        try:
            scores.append(float(r[2]))
        except (ValueError, IndexError):
            pass

    best_score = max(scores) if scores else 0
    try:
        baseline = float(rows[0][3]) if rows else 0
    except (ValueError, IndexError):
        baseline = 0

    if as_json:
        output = {
            "experiments": total,
            "kept": kept,
            "crashed": crashed,
            "baseline": baseline,
            "best_score": best_score,
            "improvement_pct": round((best_score - baseline) / baseline * 100, 1) if baseline > 0 else 0,
            "last_experiments": [
                {
                    "number": int(r[0]) if r else 0,
                    "description": r[1] if len(r) > 1 else "",
                    "score": float(r[2]) if len(r) > 2 else 0,
                    "delta": r[4] if len(r) > 4 else "",
                    "kept": len(r) > 5 and r[5] == "True",
                }
                for r in rows[-10:]
            ],
        }
        click.echo(json.dumps(output, indent=2))
        return

    click.echo(f"Experiments: {total}")
    click.echo(f"Kept:        {kept}")
    click.echo(f"Crashed:     {crashed}")
    click.echo(f"Baseline:    {baseline:.4f}")
    click.echo(f"Best Score:  {best_score:.4f}")
    if baseline > 0:
        improvement = (best_score - baseline) / baseline * 100
        click.echo(f"Improvement: {improvement:+.1f}%")

    click.echo(f"\nLast {min(5, total)} experiments:")
    click.echo("-" * 80)
    for r in rows[-5:]:
        num = r[0] if r else "?"
        desc = r[1][:50] if len(r) > 1 else ""
        score = r[2] if len(r) > 2 else "?"
        delta = r[4] if len(r) > 4 else "?"
        kept_flag = "KEPT" if len(r) > 5 and r[5] == "True" else "    "
        click.echo(f"  #{num:>3} {kept_flag} score={score} delta={delta}  {desc}")


def _show_cloud_status(run_id: str | None):
    """Open run in cloud dashboard or show cloud run status."""
    if not CONFIG_FILE.exists():
        click.echo("Not logged in. Run 'ars login' first.")
        return

    config = json.loads(CONFIG_FILE.read_text())
    if not config.get("token"):
        click.echo("Not logged in. Run 'ars login' first.")
        return

    api_url = config.get("api_url", "https://api.research.frozo.ai/v1")
    frontend_url = api_url.replace("/v1", "").replace("api-", "web-").replace("api.", "")

    if run_id:
        url = f"{frontend_url}/dashboard/runs/{run_id}"
        click.echo(f"Opening run in dashboard: {url}")
        webbrowser.open(url)
    else:
        url = f"{frontend_url}/dashboard"
        click.echo(f"Opening dashboard: {url}")
        webbrowser.open(url)
