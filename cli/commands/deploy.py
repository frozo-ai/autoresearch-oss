"""ars deploy — push project to AutoResearch Cloud."""

import io
import json
import zipfile
from pathlib import Path

import click
import httpx

from cli.commands.login import CONFIG_FILE, _get_config


@click.command("deploy")
@click.option("--dir", "-d", "directory", default=".", help="Project directory")
@click.option("--name", "-n", default=None, help="Project name (default: directory name)")
def deploy_cmd(directory: str, name: str | None):
    """Push a local project to AutoResearch Cloud."""
    config = _get_config()
    if not config.get("token"):
        click.echo("Not logged in. Run 'ars login' first.", err=True)
        raise SystemExit(1)

    workspace = Path(directory).resolve()
    program_path = workspace / "program.md"

    if not program_path.exists():
        click.echo("No program.md found. Run 'ars init' first.", err=True)
        raise SystemExit(1)

    project_name = name or workspace.name
    program_md = program_path.read_text()

    # Detect eval type and target file
    eval_type = "bash"
    target_file = ""
    if (workspace / "eval.py").exists():
        eval_type = "python_script"
    elif (workspace / "eval.sh").exists():
        eval_type = "bash"

    # Try to find target file from program.md
    for f in workspace.iterdir():
        if f.suffix in (".txt", ".md") and f.name != "program.md":
            target_file = f.name
            break

    if not target_file:
        target_file = click.prompt("Target file path", type=str)

    api_url = config.get("api_url", "https://api.research.frozo.ai/v1")
    headers = {"Authorization": f"Bearer {config['token']}", "Content-Type": "application/json"}

    # Create project
    click.echo(f"Deploying '{project_name}' to AutoResearch Cloud...")

    try:
        resp = httpx.post(
            f"{api_url}/projects",
            headers=headers,
            json={
                "name": project_name,
                "description": f"Deployed from CLI: {workspace}",
                "target_file_path": target_file,
                "eval_type": eval_type,
                "program_md": program_md,
            },
            timeout=30,
        )
        resp.raise_for_status()
        project = resp.json()
    except httpx.HTTPStatusError as e:
        click.echo(f"Deploy failed: {e.response.text}", err=True)
        raise SystemExit(1)

    click.echo(f"Project created: {project['id']}")
    click.echo(f"Name: {project['name']}")
    click.echo(f"Target: {project['target_file_path']}")
    click.echo(f"\nRun on cloud: ars run --cloud --project {project['id']}")
