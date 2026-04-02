"""program.md parser and validator.

Validates that a program.md file contains all required sections
and extracts configuration for the experiment loop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_SECTIONS = ["Goal", "Setup", "Constraints", "Experiment Loop", "Metric"]


@dataclass
class ProgramConfig:
    """Parsed configuration from a program.md file."""

    title: str = ""
    goal: str = ""
    setup: str = ""
    constraints: list[str] = field(default_factory=list)
    experiment_loop: str = ""
    metric_name: str = ""
    higher_is_better: bool = True
    eval_command: str = ""
    raw_content: str = ""


class ParseError(Exception):
    """Raised when program.md fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"program.md validation failed: {'; '.join(errors)}")


def parse(content: str) -> ProgramConfig:
    """Parse and validate a program.md string.

    Args:
        content: Raw markdown content of program.md

    Returns:
        ProgramConfig with all extracted fields

    Raises:
        ParseError: If required sections are missing or malformed
    """
    errors = []
    config = ProgramConfig(raw_content=content)

    # Extract title from first H1
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        config.title = title_match.group(1).strip()
    else:
        errors.append("Missing title (expected '# Title' as first heading)")

    # Extract sections by H2 headers
    sections: dict[str, str] = {}
    section_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(section_pattern.finditer(content))

    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections[name] = content[start:end].strip()

    # Validate required sections
    for section in REQUIRED_SECTIONS:
        if section not in sections:
            errors.append(f"Missing required section: '## {section}'")

    if errors:
        raise ParseError(errors)

    # Extract fields
    config.goal = sections.get("Goal", "").strip()
    config.setup = sections.get("Setup", "").strip()
    config.experiment_loop = sections.get("Experiment Loop", "").strip()

    # Parse constraints as bullet list
    constraints_text = sections.get("Constraints", "")
    config.constraints = [
        line.strip().lstrip("- ").lstrip("* ")
        for line in constraints_text.splitlines()
        if line.strip().startswith(("-", "*"))
    ]

    # Parse metric section for metric_name and higher_is_better
    metric_text = sections.get("Metric", "")
    name_match = re.search(r"metric_name:\s*(.+)", metric_text)
    if name_match:
        config.metric_name = name_match.group(1).strip()
    else:
        errors.append("Metric section missing 'metric_name: <name>'")

    hib_match = re.search(r"higher_is_better:\s*(true|false)", metric_text, re.IGNORECASE)
    if hib_match:
        config.higher_is_better = hib_match.group(1).lower() == "true"
    else:
        errors.append("Metric section missing 'higher_is_better: true|false'")

    # Extract eval command from Experiment Loop
    run_match = re.search(r"Run:\s*[`\"]?(.+?)[`\"]?\s*$", config.experiment_loop, re.MULTILINE)
    if run_match:
        config.eval_command = run_match.group(1).strip()

    if errors:
        raise ParseError(errors)

    return config


def parse_file(path: str | Path) -> ProgramConfig:
    """Parse a program.md file from disk."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"program.md not found: {path}")
    return parse(path.read_text())


def validate(content: str) -> list[str]:
    """Validate program.md content and return list of errors (empty = valid)."""
    try:
        parse(content)
        return []
    except ParseError as e:
        return e.errors
