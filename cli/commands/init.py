"""ars init — scaffold a new autoresearch project."""

import shutil
from pathlib import Path

import click


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# Maps wizard choice → (template name, default target file)
_WIZARD_OPTIONS = {
    "LLM Prompt":         ("prompt-opt",   "system_prompt.txt"),
    "Config File":        ("config-tune",  "config.yaml"),
    "Copy/Text":          ("copy-opt",     "copy.txt"),
    "Code (fix tests)":   ("test-pass",    "solution.py"),
    "Custom":             ("sop",          "target.txt"),
}

_PROVIDER_CHOICES = ["OpenAI", "Anthropic", "Gemini"]


def _run_wizard() -> tuple[str, str, str, str, str | None]:
    """Run the interactive setup wizard.

    Returns (template, directory, target_file, provider, eval_method).
    """
    # 1. What to optimize
    goal_choices = list(_WIZARD_OPTIONS.keys())
    click.echo("\nWhat do you want to optimize?\n")
    for i, choice in enumerate(goal_choices, 1):
        click.echo(f"  {i}. {choice}")
    click.echo()

    goal_input = click.prompt("Choose (1-5)", type=str, default="1")

    # Accept both number and full text
    try:
        idx = int(goal_input) - 1
        if 0 <= idx < len(goal_choices):
            goal = goal_choices[idx]
        else:
            click.echo(f"Invalid choice. Using default: LLM Prompt")
            goal = goal_choices[0]
    except ValueError:
        # Try matching by text
        matched = [g for g in goal_choices if g.lower() == goal_input.lower()]
        if matched:
            goal = matched[0]
        else:
            click.echo(f"Invalid choice. Using default: LLM Prompt")
            goal = goal_choices[0]

    template, default_target = _WIZARD_OPTIONS[goal]

    # 1.5 — For prompts, ask about eval method
    eval_method = None
    if goal == "LLM Prompt":
        click.echo("\nHow should we measure improvement?\n")
        click.echo("  1. Test cases — I have labeled input/expected output pairs")
        click.echo("  2. AI judge — let AI score quality automatically (no test data needed)")
        click.echo()
        eval_choice = click.prompt("Choose (1-2)", type=click.Choice(["1", "2"]), default="2")
        eval_method = "test_cases" if eval_choice == "1" else "ai_judge"

    # 2. Target file name
    target_file = click.prompt("Target file name", default=default_target)

    # 3. LLM provider
    provider = click.prompt(
        "LLM provider",
        type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False),
        default="OpenAI",
    )

    # 4. Directory
    directory = click.prompt("Project directory", default=".")

    return template, directory, target_file, provider.lower(), eval_method


def _scaffold(template: str, directory: str) -> list[str]:
    """Copy template files into the target directory.

    Returns a list of created file names.
    """
    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)

    template_dir = TEMPLATES_DIR / template
    if not template_dir.exists():
        click.echo(f"Template '{template}' not found at {template_dir}", err=True)
        raise SystemExit(1)

    created: list[str] = []
    for src_file in sorted(template_dir.iterdir()):
        if src_file.name.startswith("."):
            continue
        dest = target / src_file.name
        if dest.exists():
            click.echo(f"  Skipping {src_file.name} (already exists)")
            continue
        shutil.copy2(src_file, dest)
        click.echo(f"  Created {src_file.name}")
        created.append(src_file.name)

    return created


@click.command("init")
@click.option(
    "--template", "-t",
    type=click.Choice([
        "prompt-opt", "config-tune", "copy-opt", "test-pass", "sop",
    ]),
    default=None,
    help="Template to use for scaffolding (skips interactive wizard)",
)
@click.option("--dir", "-d", "directory", default=".", help="Directory to scaffold in")
def init_cmd(template: str | None, directory: str):
    """Scaffold a new autoresearch project with program.md and eval harness.

    Without --template, runs an interactive wizard that asks what you want
    to optimize, which target file to use, and which LLM provider to use.
    """
    provider = None

    if template is None:
        template, directory, target_file, provider, eval_method = _run_wizard()
        click.echo()
    else:
        target_file = None
        eval_method = None

    click.echo(f"Scaffolding '{template}' template...")
    created = _scaffold(template, directory)

    if not created:
        click.echo("\nNo new files created (all already exist).")
        return

    # If user chose test cases, remind them to edit test_cases.json
    if eval_method == "test_cases":
        click.echo("\n  Using test-case eval. Edit test_cases.json with your labeled examples.")
        click.echo('  Format: [{"input": "...", "expected": "..."}, ...]')
    elif eval_method == "ai_judge":
        click.echo("\n  Using AI judge eval. No test data needed — the LLM will score quality automatically.")

    click.echo(f"\nProject scaffolded in {Path(directory).resolve()}")

    # Show provider hint if selected
    if provider:
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
        }
        env_var = env_vars.get(provider, "LLM_API_KEY")
        click.echo(f"\nProvider: {provider}")
        click.echo(f"  Make sure {env_var} is set in your environment.")

    click.echo("\nNext steps:")
    click.echo("  1. Edit program.md with your optimization goal")
    if target_file:
        click.echo(f"  2. Edit {target_file} with your initial content")
        click.echo("  3. Edit or replace eval.py / eval.sh with your eval harness")
        click.echo("  4. Run: ars run")
    else:
        click.echo("  2. Edit or replace eval.py / eval.sh with your eval harness")
        click.echo("  3. Run: ars run")
