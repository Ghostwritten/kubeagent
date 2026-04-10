"""Interactive REPL for KubeAgent."""

from __future__ import annotations

import subprocess

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from pydantic_ai.messages import ModelMessage

from kubeagent import __version__
from kubeagent.agent.agent import create_agent
from kubeagent.agent.deps import KubeAgentDeps
from kubeagent.cli.output import (
    console,
    render_error,
    render_help,
    render_spinner,
    render_streaming_done,
    render_streaming_token,
    render_welcome,
)
from kubeagent.config.settings import KubeAgentConfig, load_config
from kubeagent.infra.cluster import KubeconfigManager


class KubeAgentREPL:
    """Interactive multi-turn REPL for KubeAgent."""

    def __init__(self, config: KubeAgentConfig | None = None) -> None:
        self.config = config or load_config()
        self.history: list[ModelMessage] = []
        self.session: PromptSession[str] = PromptSession(history=InMemoryHistory())
        self._cluster_name: str | None = None
        self._agent = None

    def _get_cluster_name(self) -> str | None:
        """Get the current cluster name for the prompt."""
        try:
            km = KubeconfigManager(self.config.cluster.kubeconfig)
            ctx = km.get_current_context()
            if ctx:
                return ctx.cluster
        except Exception:
            pass
        return None

    def _build_prompt(self) -> str:
        """Build the input prompt string."""
        cluster = self._cluster_name or "no-cluster"
        return f"[kubeagent:{cluster}]> "

    def _init_agent(self) -> None:
        """Initialize the agent lazily."""
        if self._agent is None:
            self._agent = create_agent(self.config)

    def start(self) -> None:
        """Start the interactive REPL loop."""
        self._cluster_name = self._get_cluster_name()
        render_welcome(__version__, self._cluster_name)

        while True:
            try:
                user_input = self.session.prompt(self._build_prompt()).strip()
            except KeyboardInterrupt:
                # Ctrl+C on empty line exits, on non-empty clears
                console.print()
                continue
            except EOFError:
                # Ctrl+D exits
                console.print("\nGoodbye!")
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                handled = self._handle_command(user_input)
                if handled == "exit":
                    break
                continue

            # Handle shell passthrough
            if user_input.startswith("!"):
                self._handle_shell(user_input[1:].strip())
                continue

            # Handle natural language query
            self._handle_query(user_input)

    def _handle_command(self, command: str) -> str | None:
        """Handle slash commands. Returns 'exit' to break the loop."""
        cmd = command.lower().strip()

        if cmd in ("/exit", "/quit", "/q"):
            console.print("Goodbye!")
            return "exit"
        elif cmd == "/help":
            render_help()
        elif cmd == "/clear":
            self.history.clear()
            console.print("[dim]Conversation history cleared.[/dim]")
        elif cmd == "/model":
            model = self.config.model.default
            console.print(f"Model: {model}")
        elif cmd == "/cluster":
            self._show_cluster_info()
        else:
            render_error(f"Unknown command: {command}. Type /help for available commands.")

        return None

    def _show_cluster_info(self) -> None:
        """Show current cluster information."""
        try:
            km = KubeconfigManager(self.config.cluster.kubeconfig)
            ctx = km.get_current_context()
            if ctx:
                console.print(f"Context:  {ctx.name}")
                console.print(f"Cluster:  {ctx.cluster}")
                console.print(f"Namespace: {ctx.namespace}")
                console.print(f"Server:   {km.get_cluster_server(ctx.name) or 'unknown'}")
            else:
                render_error("No current context set.")
        except Exception as e:
            render_error(f"Failed to get cluster info: {e}")

    def _handle_shell(self, command: str) -> None:
        """Execute a shell command."""
        if not command:
            return

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                console.print(result.stdout, end="")
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]", end="")
            if result.returncode != 0:
                console.print(f"[dim]Exit code: {result.returncode}[/dim]")
        except subprocess.TimeoutExpired:
            render_error("Command timed out after 30 seconds.")
        except Exception as e:
            render_error(f"Shell error: {e}")

    def _handle_query(self, user_input: str) -> None:
        """Handle a natural language query with streaming."""
        self._init_agent()
        deps = KubeAgentDeps(config=self.config)

        try:
            with render_spinner("Thinking..."):
                pass  # spinner shown while waiting

            import asyncio

            asyncio.run(self._run_streaming(user_input, deps))
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]")
        except ConnectionError as e:
            render_error(f"Cannot connect to cluster: {e}")
        except Exception as e:
            render_error(f"Unexpected error: {e}")

    async def _run_streaming(self, user_input: str, deps: KubeAgentDeps) -> None:
        """Run the agent with streaming output and update history."""
        assert self._agent is not None

        try:
            async with self._agent.run_stream(
                user_input,
                deps=deps,
                message_history=self.history if self.history else None,
            ) as response:
                # Stream text tokens
                async for token in response.stream_text(delta=True):
                    render_streaming_token(token)

                render_streaming_done()

                # Update history for multi-turn
                self.history = response.all_messages()
        except Exception as e:
            render_error(str(e))
