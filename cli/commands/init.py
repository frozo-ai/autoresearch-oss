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

    # 2. Target file — ask if user has an existing file to import
    click.echo(f"\nTarget file (the file the AI will optimize): {default_target}")
    existing_file = click.prompt(
        "Path to your existing file (or press Enter to use the template)",
        default="",
        show_default=False,
    )

    if existing_file and Path(existing_file).exists():
        target_file = default_target
        # Will copy user's file after scaffolding
        _user_file_content = Path(existing_file).read_text()
        _import_user_file = True
        click.echo(f"  Will import: {existing_file} ({len(_user_file_content)} chars)")
    else:
        target_file = default_target
        _user_file_content = None
        _import_user_file = False
        if existing_file:
            click.echo(f"  File not found: {existing_file}. Will use template default.")

    # 3. LLM provider
    click.echo()
    provider = click.prompt(
        "LLM provider (OpenAI, Anthropic, Gemini)",
        type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False),
        default="Anthropic",
    )

    # 4. Directory
    directory = click.prompt("Project directory", default=".")

    return template, directory, target_file, provider.lower(), eval_method, _import_user_file, _user_file_content


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
    import_user_file = False
    user_file_content = None

    if template is None:
        template, directory, target_file, provider, eval_method, import_user_file, user_file_content = _run_wizard()
        click.echo()
    else:
        target_file = None
        eval_method = None

    click.echo(f"Scaffolding '{template}' template...")
    created = _scaffold(template, directory)

    if not created:
        click.echo("\nNo new files created (all already exist).")
        return

    # Overwrite target file with user's content if they imported one
    if import_user_file and user_file_content and target_file:
        target_path = Path(directory).resolve() / target_file
        target_path.write_text(user_file_content)
        click.echo(f"  Imported your file → {target_file}")

    # Show eval method info
    if eval_method == "test_cases":
        click.echo("\n  Eval: test cases")
        click.echo("  Edit test_cases.json with your labeled examples:")
        click.echo('  Format: [{"input": "...", "expected": "..."}, ...]')
        click.echo("  Tip: Start with 5-10 examples. More = more accurate scoring.")
    elif eval_method == "ai_judge":
        click.echo("\n  Eval: AI judge (uses your API key for scoring)")
        click.echo("  No test data needed — the LLM scores each version on quality criteria.")
        click.echo("  Note: Each experiment costs ~2 LLM calls (1 proposal + 1 judge).")

    click.echo(f"\nProject scaffolded in {Path(directory).resolve()}")

    # Show clear next steps based on what they chose
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }

    click.echo("\n" + "=" * 50)
    click.echo("  Next steps:")
    click.echo("=" * 50)

    step = 1

    # API key
    if provider:
        env_var = env_vars.get(provider, "LLM_API_KEY")
        click.echo(f"\n  {step}. Set your API key:")
        click.echo(f"     export {env_var}=your-key-here")
        step += 1

    # Edit target file (only if they didn't import one)
    if not import_user_file and target_file:
        click.echo(f"\n  {step}. Edit your target file:")
        click.echo(f"     {target_file}")
        click.echo(f"     (Replace the template content with your actual prompt/config/code)")
        step += 1

    # Edit test cases (if test case eval)
    if eval_method == "test_cases":
        click.echo(f"\n  {step}. Add your test cases:")
        click.echo(f"     test_cases.json")
        click.echo(f'     Format: [{{"input": "your input", "expected": "expected output"}}]')
        step += 1

    # Validate
    click.echo(f"\n  {step}. Validate your setup:")
    click.echo(f"     ars run --dry-run")
    step += 1

    # Run
    click.echo(f"\n  {step}. Run experiments:")
    click.echo(f"     ars run --max-experiments 20")
    click.echo()
