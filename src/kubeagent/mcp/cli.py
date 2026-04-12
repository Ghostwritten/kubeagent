"""CLI commands for MCP server lifecycle management."""

from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

import click


def _pid_file() -> Path:
    """Path to the MCP server PID file."""
    return Path.home() / ".kubeagent" / "mcp-server.pid"


def _write_pid(pid: int, port: int) -> None:
    """Write PID and port to file."""
    pid_path = _pid_file()
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({"pid": pid, "port": port}))


def _read_pid() -> dict | None:
    """Read PID info from file. Returns None if not running."""
    pid_path = _pid_file()
    if not pid_path.exists():
        return None
    try:
        data = json.loads(pid_path.read_text())
        pid = data["pid"]
        # Check if process is still alive
        os.kill(pid, 0)
        return data
    except (OSError, KeyError, json.JSONDecodeError):
        # Process not running or file corrupt — clean up
        pid_path.unlink(missing_ok=True)
        return None


def _clear_pid() -> None:
    """Remove the PID file."""
    _pid_file().unlink(missing_ok=True)


@click.group(name="mcp")
def mcp_group() -> None:
    """MCP server management commands."""


@mcp_group.command()
@click.option("--port", default=8765, help="Server port (SSE mode)")
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]))
@click.option("--daemon", is_flag=True, help="Run as background daemon (SSE mode only)")
def start(port: int, transport: str, daemon: bool) -> None:
    """Start the MCP server."""
    from kubeagent.mcp.server import KubeAgentMCPServer

    existing = _read_pid()
    if existing:
        click.echo(f"MCP server already running (PID {existing['pid']}, port {existing['port']})")
        return

    server = KubeAgentMCPServer(port=port)
    click.echo(f"KubeAgent MCP server — {server.tool_count} tools, {server.skill_count} skills")

    if daemon and transport == "sse":
        pid = os.fork()
        if pid > 0:
            # Parent process
            _write_pid(pid, port)
            click.echo(f"Started MCP server daemon (PID {pid}) on port {port}")
            return
        else:
            # Child — detach and run
            os.setsid()
            server.run(transport="sse")
    else:
        if transport == "sse":
            _write_pid(os.getpid(), port)
        click.echo(f"Starting MCP server ({transport} mode)...")
        try:
            server.run(transport=transport)
        finally:
            if transport == "sse":
                _clear_pid()


@mcp_group.command()
def stop() -> None:
    """Stop the MCP server daemon."""
    info = _read_pid()
    if not info:
        click.echo("MCP server is not running.")
        return

    pid = info["pid"]
    try:
        os.kill(pid, signal.SIGTERM)
        click.echo(f"Stopped MCP server (PID {pid}).")
    except OSError as e:
        click.echo(f"Failed to stop server: {e}")
    finally:
        _clear_pid()


@mcp_group.command()
def status() -> None:
    """Show MCP server status."""
    info = _read_pid()
    if info:
        click.echo(f"MCP server is running (PID {info['pid']}, port {info['port']})")
    else:
        click.echo("MCP server is not running.")
