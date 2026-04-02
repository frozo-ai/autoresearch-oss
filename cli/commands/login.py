"""ars login — authenticate with AutoResearch Cloud."""

import json
from pathlib import Path

import click
import httpx

CONFIG_DIR = Path.home() / ".autoresearch"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.research.frozo.ai/v1"


def _get_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    CONFIG_FILE.chmod(0o600)  # Restrict to owner only


@click.command("login")
@click.option("--email", prompt="Email", help="Account email")
@click.option("--password", prompt=True, hide_input=True, help="Account password")
@click.option("--api-url", default=DEFAULT_API_URL, help="API base URL")
def login_cmd(email: str, password: str, api_url: str):
    """Authenticate with AutoResearch Cloud."""
    try:
        resp = httpx.post(
            f"{api_url}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            click.echo("Invalid email or password.", err=True)
        else:
            click.echo(f"Login failed: {e.response.text}", err=True)
        raise SystemExit(1)
    except httpx.RequestError as e:
        click.echo(f"Connection error: {e}", err=True)
        raise SystemExit(1)

    config = _get_config()
    config["token"] = data["access_token"]
    config["api_url"] = api_url
    config["email"] = email
    _save_config(config)

    click.echo(f"Logged in as {email}")
    click.echo(f"Token saved to {CONFIG_FILE}")
