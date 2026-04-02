"""AutoResearch CLI — ars command entrypoint."""

import click

from cli.commands.apply import apply_cmd
from cli.commands.config import config_cmd
from cli.commands.deploy import deploy_cmd
from cli.commands.diff import diff_cmd
from cli.commands.init import init_cmd
from cli.commands.login import login_cmd
from cli.commands.results import results_cmd
from cli.commands.run import run_cmd
from cli.commands.status import status_cmd
from cli.commands.upgrade import upgrade_cmd


@click.group(invoke_without_command=True)
@click.version_option(version="0.2.0", prog_name="ars")
def cli():
    """AutoResearch — Autonomous experiment loop runner.

    Run optimization experiments overnight. Wake up to a better system.

    Quick start:

      ars init                    Scaffold a new project (interactive wizard)
      ars run                     Run experiments locally
      ars run --dry-run           Validate setup without running experiments
      ars results                 View full experiment results table
      ars diff                    See before/after comparison
      ars apply                   Write the best version to your file
      ars status                  Show run summary

    Cloud:

      ars login                   Sign in to AutoResearch Cloud
      ars run --cloud             Run on cloud (auto-deploys project)
      ars run --cloud --lanes 4   Parallel lanes on cloud
      ars deploy                  Push project to cloud without running
      ars upgrade                 View pricing plans

    Config:

      ars config show             Show config + API key status
      ars config set KEY VALUE    Set a default (provider, model, api_url)
    """
    ctx = click.get_current_context()
    if ctx.invoked_subcommand is None:
        from cli.repl import start_repl
        start_repl(cli)


cli.add_command(init_cmd, "init")
cli.add_command(run_cmd, "run")
cli.add_command(results_cmd, "results")
cli.add_command(status_cmd, "status")
cli.add_command(diff_cmd, "diff")
cli.add_command(apply_cmd, "apply")
cli.add_command(config_cmd, "config")
cli.add_command(login_cmd, "login")
cli.add_command(deploy_cmd, "deploy")
cli.add_command(upgrade_cmd, "upgrade")


if __name__ == "__main__":
    cli()
