"""ars config — manage CLI defaults in ~/.autoresearch/config.json."""

import json
import os
from pathlib import Path

import click


CONFIG_DIR = Path.home() / ".autoresearch"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Keys that can be set via 'ars config set'
ALLOWED_KEYS = {"provider", "model", "api_url"}

# Environment variable names for API key detection
_API_KEY_ENV_VARS = {
    "OPENAI_API_KEY": "OpenAI",
    "ANTHROPIC_API_KEY": "Anthropic",
    "GOOGLE_API_KEY": "Gemini",
}


def _get_config() -> dict:
    """Load config from disk."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_config(config: dict) -> None:
    """Write config to disk with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    CONFIG_FILE.chmod(0o600)


@click.group("config")
def config_cmd():
    """Manage CLI configuration defaults."""
    pass


@config_cmd.command("show")
def config_show():
    """Display all configuration values and status."""
    config = _get_config()

    click.echo()
    click.echo("Configuration")
    click.echo("-" * 40)

    if config:
        for key in sorted(config.keys()):
            value = config[key]
            # Mask sensitive values
            if key == "token" and value:
                display = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display = value
            click.echo(f"  {key}: {display}")
    else:
        click.echo("  (no config set)")

    # API key status
    click.echo()
    click.echo("API Keys")
    click.echo("-" * 40)
    for env_var, provider_name in _API_KEY_ENV_VARS.items():
        is_set = bool(os.environ.get(env_var))
        status = "set" if is_set else "not set"
        click.echo(f"  {provider_name} ({env_var}): {status}")

    # Auth status
    click.echo()
    click.echo("Auth")
    click.echo("-" * 40)
    token = config.get("token")
    email = config.get("email")
    if token:
        click.echo(f"  Logged in as: {email or 'unknown'}")
    else:
        click.echo("  Not logged in. Run 'ars login' to authenticate.")

    # Session state
    click.echo("Session")
    click.echo("-" * 40)
    try:
        session_file = Path.home() / ".autoresearch" / "session.json"
        if session_file.exists():
            session = json.loads(session_file.read_text())
            last_run = session.get("last_run", {})
            if last_run:
                click.echo(f"  Last provider: {session.get('last_provider', 'N/A')}")
                click.echo(f"  Last model: {session.get('last_model', 'N/A')}")
                click.echo(f"  Last run: {last_run.get('total_experiments', '?')} experiments, {last_run.get('improvements_kept', '?')} kept")
                click.echo(f"  Last workspace: {session.get('last_workspace', 'N/A')}")
            else:
                click.echo("  No runs yet.")
        else:
            click.echo("  No runs yet.")
    except Exception:
        click.echo("  (could not read session)")
    click.echo()

    click.echo(f"Config file: {CONFIG_FILE}")
    click.echo()


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Allowed keys: provider, model, api_url
    """
    if key not in ALLOWED_KEYS:
        click.echo(
            f"Unknown config key: '{key}'. "
            f"Allowed keys: {', '.join(sorted(ALLOWED_KEYS))}",
            err=True,
        )
        raise SystemExit(1)

    config = _get_config()
    config[key] = value
    _save_config(config)
    click.echo(f"Set {key} = {value}")


@config_cmd.command("get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value."""
    config = _get_config()

    if key not in config:
        click.echo(f"Key '{key}' is not set.", err=True)
        raise SystemExit(1)

    value = config[key]
    # Mask token
    if key == "token" and value:
        click.echo(value[:8] + "..." if len(value) > 8 else "***")
    else:
        click.echo(value)
