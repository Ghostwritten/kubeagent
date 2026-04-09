"""CLI entry point using click."""

import click

from kubeagent import __version__
from kubeagent.cli.setup_wizard import run_doctor, run_wizard
from kubeagent.config.settings import config_exists


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="kubeagent")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """KubeAgent — Natural language CLI for Kubernetes management."""
    if ctx.invoked_subcommand is None:
        # No subcommand: check if first-run setup needed
        if not config_exists():
            run_wizard()
        else:
            click.echo("KubeAgent is ready. Use 'kubeagent --help' to see available commands.")


@cli.command()
def init() -> None:
    """Run the setup wizard to configure KubeAgent."""
    run_wizard()


@cli.command()
def doctor() -> None:
    """Run diagnostics to check your configuration."""
    run_doctor()


@cli.command()
def info() -> None:
    """Show current configuration info."""
    from kubeagent.config.settings import detect_kubeconfig, get_env_api_key, load_config

    config = load_config()
    click.echo(f"KubeAgent v{__version__}")
    click.echo(f"Config: {config.model_dump(mode='json', exclude_none=True)}")

    kubeconfig = detect_kubeconfig()
    if kubeconfig:
        click.echo(f"Kubeconfig: {kubeconfig}")
    else:
        click.echo("Kubeconfig: not found")

    api_key = get_env_api_key()
    if api_key:
        click.echo("API Key: detected from environment")
    else:
        click.echo("API Key: not found")
