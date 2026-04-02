"""ars upgrade — open AutoResearch Cloud pricing page."""

import webbrowser

import click


PRICING_URL = "https://research.frozo.ai/#pricing"


@click.command("upgrade")
def upgrade_cmd():
    """Open the AutoResearch Cloud pricing page in your browser."""
    click.echo("Opening AutoResearch Cloud pricing...")
    click.echo("")
    click.echo("  Free:    $0/mo   — 5 cloud runs, 30 experiments/run")
    click.echo("  Starter: $9/mo   — 100 cloud runs, 100 experiments/run, 2 lanes")
    click.echo("  Pro:     $29/mo  — Unlimited runs, 200 experiments/run, 8 lanes")
    click.echo("  Team:    $79/mo  — Everything + 10 seats, SSO, 16 lanes")
    click.echo("")
    webbrowser.open(PRICING_URL)
