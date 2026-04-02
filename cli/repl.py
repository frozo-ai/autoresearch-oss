"""Interactive REPL mode for the ars CLI.

When ars is invoked with no arguments, drop into an interactive session
where users can type commands without the 'ars' prefix.
"""

import shlex
import sys

import click


BANNER = """
  ╔══════════════════════════════════════════════╗
  ║  AutoResearch v0.2.0 — Interactive Mode      ║
  ║  Type any command without 'ars' prefix.       ║
  ║  Type 'help' for commands, 'quit' to exit.    ║
  ╚══════════════════════════════════════════════╝
"""

QUICK_HELP = """
  Commands:
    init                    Scaffold a new project
    run [OPTIONS]           Run experiments
    run --dry-run           Validate setup
    results                 View experiment results
    status                  Show run summary
    diff                    See before/after comparison
    apply                   Apply best version to file
    config show             Show configuration
    config set KEY VALUE    Set a default
    login                   Sign in to cloud
    upgrade                 View pricing plans
    help                    Show this help
    quit / exit             Exit REPL
"""


def start_repl(cli_group):
    """Start the interactive REPL."""
    click.echo(BANNER)

    while True:
        try:
            # Show prompt
            line = input(click.style("ars> ", fg="cyan", bold=True))
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye!")
            break

        line = line.strip()
        if not line:
            continue

        if line in ("quit", "exit", "q"):
            click.echo("Goodbye!")
            break

        if line == "help":
            click.echo(QUICK_HELP)
            continue

        # Parse the command line
        try:
            args = shlex.split(line)
        except ValueError as e:
            click.echo(f"Parse error: {e}")
            continue

        # Execute via Click
        try:
            cli_group(args, standalone_mode=False)
        except SystemExit:
            pass  # Click raises SystemExit on --help, errors, etc.
        except click.exceptions.UsageError as e:
            click.echo(f"Error: {e}")
        except Exception as e:
            click.echo(f"Error: {e}")
