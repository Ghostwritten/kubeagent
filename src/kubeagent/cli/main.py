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
        if not config_exists():
            run_wizard()
        else:
            from kubeagent.cli.repl import KubeAgentREPL

            repl = KubeAgentREPL()
            repl.start()


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
    from kubeagent.config.settings import load_config
    from kubeagent.infra.cluster import KubeconfigManager

    config = load_config()
    click.echo(f"KubeAgent v{__version__}")
    click.echo(f"Config: {config.model_dump(mode='json', exclude_none=True)}")

    km = KubeconfigManager(config.cluster.kubeconfig)
    current = km.get_current_context()
    if current:
        click.echo(f"Kubeconfig: {km.kubeconfig_path}")
        click.echo(f"Context: {current.name}")
        click.echo(f"Namespace: {current.namespace}")


@cli.command(name="clusters")
def clusters_cmd() -> None:
    """List all clusters from kubeconfig."""
    from rich.console import Console
    from rich.table import Table

    from kubeagent.config.settings import load_config
    from kubeagent.infra.cluster import KubeconfigManager

    config = load_config()
    km = KubeconfigManager(config.cluster.kubeconfig)

    ctxs = km.get_contexts()
    if not ctxs:
        click.echo("No contexts found in kubeconfig.")
        return

    table = Table(title="Kubernetes Clusters")
    table.add_column("Current", style="bold green", width=8)
    table.add_column("Context", style="cyan")
    table.add_column("Cluster", style="blue")
    table.add_column("Namespace", style="dim")

    for ctx in ctxs:
        marker = "✅" if ctx.is_current else ""
        table.add_row(marker, ctx.name, ctx.cluster, ctx.namespace)

    console = Console()
    console.print(table)


@cli.command()
@click.argument("context_name")
def switch(context_name: str) -> None:
    """Switch to a cluster context by name."""
    from kubeagent.config.settings import load_config
    from kubeagent.infra.cluster import KubeconfigManager

    config = load_config()
    km = KubeconfigManager(config.cluster.kubeconfig)

    # Find matching context (support partial match)
    matches = [ctx for ctx in km.get_contexts() if context_name in ctx.name]

    if not matches:
        available = [ctx.name for ctx in km.get_contexts()]
        click.echo(f"Context '{context_name}' not found.")
        click.echo(f"Available contexts: {', '.join(available)}")
        return

    if len(matches) > 1:
        click.echo(f"Multiple matches found: {', '.join(m.name for m in matches)}")
        click.echo("Please be more specific.")
        return

    ctx = matches[0]
    if ctx.is_current:
        click.echo(f"Already on context '{ctx.name}'.")
        return

    if km.switch_context(ctx.name):
        click.echo(f"Switched to context '{ctx.name}'.")
        click.echo("Run 'kubeagent cluster-info' to verify connection.")
    else:
        click.echo(f"Failed to switch to context '{ctx.name}'.")


# Register MCP subcommands
from kubeagent.mcp.cli import mcp_group

cli.add_command(mcp_group)


@cli.command(name="cluster-info")
def cluster_info() -> None:
    """Show detailed information about the current cluster."""
    from rich.console import Console
    from rich.panel import Panel

    from kubeagent.config.settings import load_config
    from kubeagent.infra.cluster import KubeconfigManager

    config = load_config()
    km = KubeconfigManager(config.cluster.kubeconfig)

    current = km.get_current_context()
    if not current:
        click.echo("No current context. Run 'kubeagent clusters' to see available contexts.")
        return

    console = Console()

    # Try to connect and get server version
    cluster_server = km.get_cluster_server(current.name)
    k8s_version = "unknown"
    nodes_count = "unknown"

    try:
        from kubernetes import client, config

        config.load_kube_config(config_file=str(km.kubeconfig_path))
        version_api = client.VersionApi()
        version_info = version_api.get_code()
        k8s_version = version_info.git_version

        v1 = client.CoreV1Api()
        all_nodes = v1.list_node()
        nodes_count = str(len(all_nodes.items))
    except Exception as e:
        k8s_version = f"error: {e}"
        nodes_count = "unknown"

    info_lines = [
        f"[cyan]Context:[/cyan] {current.name}",
        f"[cyan]Cluster:[/cyan] {current.cluster}",
        f"[cyan]Namespace:[/cyan] {current.namespace}",
        f"[cyan]Server:[/cyan] {cluster_server or 'unknown'}",
        f"[cyan]K8s Version:[/cyan] {k8s_version}",
        f"[cyan]Nodes:[/cyan] {nodes_count}",
        f"[cyan]Kubeconfig:[/cyan] {km.kubeconfig_path}",
    ]

    console.print(Panel("\n".join(info_lines), title="Cluster Info", border_style="blue"))
