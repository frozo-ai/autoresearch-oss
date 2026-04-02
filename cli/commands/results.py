"""ars results — display full experiment results table."""

import csv
import io
import json
from pathlib import Path

import click
from tabulate import tabulate


# Column indices in results.tsv (matches runner output)
COL_NUM = 0
COL_DESC = 1
COL_SCORE = 2
COL_BASELINE = 3
COL_DELTA = 4
COL_KEPT = 5
COL_DURATION = 6
COL_TIMESTAMP = 7
COL_CRASHED = 8


def _parse_results(results_path: Path) -> tuple[list[str], list[list[str]]]:
    """Parse results.tsv and return (header, rows).

    Detects whether the first line is a header row.
    Returns a normalised header even if the file has none.
    """
    text = results_path.read_text().strip()
    if not text:
        return [], []

    lines = text.splitlines()
    first_fields = lines[0].split("\t")

    # Detect header: first field is non-numeric
    if first_fields and not first_fields[0].replace(".", "").replace("-", "").isdigit():
        header = first_fields
        data_lines = lines[1:]
    else:
        header = [
            "experiment_number", "description", "score", "baseline_score",
            "delta", "kept", "duration_s", "timestamp", "crashed",
        ]
        data_lines = lines

    rows = [line.split("\t") for line in data_lines if line.strip()]
    return header, rows


def _safe_float(value: str, default: float = 0.0) -> float:
    """Convert a string to float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, IndexError, TypeError):
        return default


def _get_field(row: list[str], index: int, default: str = "") -> str:
    """Safely get a field from a row."""
    return row[index] if index < len(row) else default


@click.command("results")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON array")
@click.option("--csv-output", "--csv", "as_csv", is_flag=True, help="Output as CSV")
@click.option("--path", "-p", default="results.tsv", help="Path to results.tsv")
def results_cmd(as_json: bool, as_csv: bool, path: str):
    """Show full experiment results table from results.tsv."""
    results_path = Path(path)
    if not results_path.exists():
        click.echo("No results found. Run 'ars run' first.", err=True)
        raise SystemExit(1)

    header, rows = _parse_results(results_path)
    if not rows:
        click.echo("No experiments completed yet.")
        return

    # --- Compute summary stats ---
    scores = [_safe_float(_get_field(r, COL_SCORE)) for r in rows]
    valid_scores = [s for s in scores if s != 0.0]

    baseline = _safe_float(_get_field(rows[0], COL_BASELINE))
    best_score = max(valid_scores) if valid_scores else 0.0
    total = len(rows)
    kept = sum(1 for r in rows if _get_field(r, COL_KEPT) == "True")
    crashed = sum(1 for r in rows if _get_field(r, COL_CRASHED) == "True")

    improvement_pct = (
        (best_score - baseline) / baseline * 100 if baseline > 0 else 0.0
    )

    # --- JSON output ---
    if as_json:
        records = []
        for r in rows:
            record = {
                "experiment": _get_field(r, COL_NUM),
                "score": _safe_float(_get_field(r, COL_SCORE)),
                "delta": _safe_float(_get_field(r, COL_DELTA)),
                "kept": _get_field(r, COL_KEPT) == "True",
                "crashed": _get_field(r, COL_CRASHED) == "True",
                "duration_s": _safe_float(_get_field(r, COL_DURATION)),
                "description": _get_field(r, COL_DESC),
            }
            records.append(record)

        output = {
            "summary": {
                "baseline": baseline,
                "best": best_score,
                "improvement_pct": round(improvement_pct, 2),
                "total": total,
                "kept": kept,
                "crashed": crashed,
            },
            "experiments": records,
        }
        click.echo(json.dumps(output, indent=2))
        return

    # --- CSV output ---
    if as_csv:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["#", "Score", "Delta", "Kept", "Duration", "Description"])
        for r in rows:
            writer.writerow([
                _get_field(r, COL_NUM),
                _get_field(r, COL_SCORE),
                _get_field(r, COL_DELTA),
                _get_field(r, COL_KEPT),
                _get_field(r, COL_DURATION),
                _get_field(r, COL_DESC),
            ])
        click.echo(buf.getvalue().rstrip())
        return

    # --- Table output ---
    click.echo()
    click.echo("Summary")
    click.echo("-" * 40)
    click.echo(f"  Baseline:    {baseline:.4f}")
    click.echo(f"  Best Score:  {best_score:.4f}")
    click.echo(f"  Improvement: {improvement_pct:+.1f}%")
    click.echo(f"  Experiments: {total}")
    click.echo(f"  Kept:        {kept}")
    click.echo(f"  Crashed:     {crashed}")
    click.echo()

    # Build display table
    table_rows = []
    for r in rows:
        num = _get_field(r, COL_NUM)
        score = _get_field(r, COL_SCORE)
        delta = _get_field(r, COL_DELTA)
        kept_flag = "yes" if _get_field(r, COL_KEPT) == "True" else ""
        duration = _get_field(r, COL_DURATION)
        desc = _get_field(r, COL_DESC)

        # Truncate long descriptions
        if len(desc) > 60:
            desc = desc[:57] + "..."

        table_rows.append([num, score, delta, kept_flag, duration, desc])

    table_header = ["#", "Score", "Delta", "Kept", "Duration", "Description"]
    click.echo(tabulate(table_rows, headers=table_header, tablefmt="simple"))
    click.echo()
