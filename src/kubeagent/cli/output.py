"""Output rendering for KubeAgent CLI."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

# Console instance for consistent output
console = Console()

# Colors for the theme
STYLE_CLUSTER = "bold cyan"
STYLE_ERROR = "bold red"
STYLE_WARNING = "bold yellow"
STYLE_SUCCESS = "bold green"
STYLE_DIM = "dim"


def render_output(text: str) -> None:
    """Render LLM response text as Markdown."""
    md = Markdown(text)
    console.print(md)


def render_tool_result(result: str) -> None:
    """Render a formatted tool result."""
    # Tool results come pre-formatted from the agent
    console.print(result)


def render_error(message: str) -> None:
    """Render an error message."""
    console.print(f"[{STYLE_ERROR}]Error:[/{STYLE_ERROR}] {message}")


def render_warning(message: str) -> None:
    """Render a warning message."""
    console.print(f"[{STYLE_WARNING}]Warning:[/{STYLE_WARNING}] {message}")


def render_success(message: str) -> None:
    """Render a success message."""
    console.print(f"[{STYLE_SUCCESS}]{message}[/{STYLE_SUCCESS}]")


def render_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Render a Rich table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def render_welcome(version: str, cluster: str | None = None) -> None:
    """Render the welcome banner."""
    console.print()
    console.print(f"[bold blue]KubeAgent[/bold blue] v{version}", style="bold")
    console.print("Natural language CLI for Kubernetes management")
    if cluster:
        console.print(f"Cluster: [{STYLE_CLUSTER}]{cluster}[/{STYLE_CLUSTER}]")
    console.print()
    console.print("[dim]Type your question in natural language.[/dim]")
    console.print("[dim]Commands: /help, /clear, /exit[/dim]")
    console.print("[dim]Shell: !<command> to run shell commands[/dim]")
    console.print()


def render_help() -> None:
    """Render help message."""
    console.print()
    console.print("[bold]KubeAgent Commands:[/bold]")
    console.print()
    console.print("  [cyan]/help[/cyan]     Show this help message")
    console.print("  [cyan]/clear[/cyan]    Clear conversation history")
    console.print("  [cyan]/exit[/cyan]     Exit KubeAgent (or Ctrl+D)")
    console.print("  [cyan]/model[/cyan]    Show current model")
    console.print("  [cyan]/cluster[/cyan]  Show current cluster info")
    console.print()
    console.print("[dim]Shell commands: prefix with ![/dim]")
    console.print("[dim]  !kubectl get pods[/dim]")
    console.print("[dim]  !ps aux | grep kube[/dim]")
    console.print()


def render_spinner(message: str = "Thinking...") -> Any:
    """Return a spinner context manager."""
    return console.status(message, spinner="dots")


def render_streaming_token(token: str) -> None:
    """Render a single streaming token."""
    console.print(token, end="")


def render_streaming_done() -> None:
    """Finalize streaming output with a newline."""
    console.print()
