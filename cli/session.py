"""Session state — remembers last run context between commands.

Stored in ~/.autoresearch/session.json. Updated after each run completes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

SESSION_FILE = Path.home() / ".autoresearch" / "session.json"


def load_session() -> dict:
    """Load session state from disk."""
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_session(data: dict) -> None:
    """Save session state to disk."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Merge with existing
    session = load_session()
    session.update(data)
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    SESSION_FILE.write_text(json.dumps(session, indent=2))


def update_after_run(
    workspace: str,
    provider: str,
    model: str,
    max_experiments: int,
    total: int,
    kept: int,
    best_score: float | None,
    baseline: float | None,
) -> None:
    """Update session after a local run completes."""
    save_session({
        "last_run": {
            "workspace": workspace,
            "provider": provider,
            "model": model,
            "max_experiments": max_experiments,
            "total_experiments": total,
            "improvements_kept": kept,
            "best_score": best_score,
            "baseline_score": baseline,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        "last_workspace": workspace,
        "last_provider": provider,
        "last_model": model,
    })


def get_last_provider() -> str | None:
    """Get the provider from the last session."""
    session = load_session()
    return session.get("last_provider")


def get_last_model() -> str | None:
    """Get the model from the last session."""
    session = load_session()
    return session.get("last_model")
