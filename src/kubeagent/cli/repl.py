"""Interactive REPL for KubeAgent."""

from __future__ import annotations

import hashlib
import subprocess

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from pydantic_ai.messages import ModelMessage

from kubeagent import __version__
from kubeagent.agent.agent import create_agent
from kubeagent.agent.deps import KubeAgentDeps
from kubeagent.agent.prompt_engine import build_system_prompt
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

    def __init__(
        self,
        config: KubeAgentConfig | None = None,
        auto_approve: bool = False,
        dry_run: bool = False,
    ) -> None:
        self.config = config or load_config()
        self.history: list[ModelMessage] = []
        self.session: PromptSession[str] = PromptSession(history=InMemoryHistory())
        self._cluster_name: str | None = None
        self._namespace: str | None = None
        self._server: str | None = None
        self._agent = None
        self.auto_approve = auto_approve
        self.dry_run = dry_run
        self._memory = None

    def _get_cluster_name(self) -> str | None:
        """Get the current cluster info for the prompt."""
        try:
            km = KubeconfigManager(self.config.cluster.kubeconfig)
            ctx = km.get_current_context()
            if ctx:
                self._cluster_name = ctx.cluster
                self._namespace = ctx.namespace
                self._server = km.get_cluster_server(ctx.name)
                return ctx.cluster
        except Exception:
            pass
        return None

    def _init_memory(self) -> None:
        """Initialize the memory system."""
        if self.config.memory.enabled:
            from kubeagent.agent.memory import MemoryManager

            self._memory = MemoryManager(self.config.memory)
        else:
            self._memory = None

    def _build_prompt(self) -> str:
        """Build the input prompt string."""
        cluster = self._cluster_name or "no-cluster"
        return f"[kubeagent:{cluster}]> "

    def _init_agent(self) -> None:
        """Initialize the agent lazily with dynamic prompt."""
        if self._agent is None:
            memory_prefs = None
            if self._memory is not None:
                memory_prefs = self._memory.preferences.to_prompt_section() or None
            system_prompt = build_system_prompt(
                config=self.config,
                cluster_name=self._cluster_name,
                namespace=self._namespace,
                server=self._server,
                memory_preferences=memory_prefs,
            )
            self._agent = create_agent(self.config, system_prompt=system_prompt)

    def start(self) -> None:
        """Start the interactive REPL loop."""
        self._cluster_name = self._get_cluster_name()
        self._init_memory()
        render_welcome(__version__, self._cluster_name)

        try:
            while True:
                try:
                    user_input = self.session.prompt(self._build_prompt()).strip()
                except KeyboardInterrupt:
                    console.print()
                    continue
                except EOFError:
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
        finally:
            if self._memory is not None:
                self._memory.close()

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
        elif cmd == "/yes":
            self.auto_approve = not self.auto_approve
            state = "ON" if self.auto_approve else "OFF"
            console.print(f"Auto-approve: [{state}]")
        elif cmd in ("/dryrun", "/dry-run"):
            self.dry_run = not self.dry_run
            state = "ON" if self.dry_run else "OFF"
            console.print(f"Dry-run mode: [{state}]")
        elif cmd == "/audit":
            self._handle_audit()
        elif cmd == "/preferences":
            self._handle_preferences()
        elif cmd.startswith("/remember "):
            self._handle_remember(command[10:].strip())
        elif cmd.startswith("/forget "):
            self._handle_forget(command[8:].strip())
        else:
            render_error(f"Unknown command: {command}. Type /help for available commands.")

        return None

    def _handle_audit(self) -> None:
        """Show recent audit log entries."""
        if self._memory is None:
            render_error("Memory system is disabled.")
            return
        from kubeagent.cli.output import render_audit_table

        entries = self._memory.audit.query(limit=20)
        if not entries:
            console.print("[dim]No audit entries.[/dim]")
        else:
            render_audit_table(entries)

    def _handle_preferences(self) -> None:
        """Show all saved preferences."""
        if self._memory is None:
            render_error("Memory system is disabled.")
            return
        from kubeagent.cli.output import render_preferences

        render_preferences(self._memory.preferences.get_all())

    def _handle_remember(self, text: str) -> None:
        """Save a user preference."""
        if self._memory is None:
            render_error("Memory system is disabled.")
            return
        if not text:
            render_error("Usage: /remember <text>")
            return
        key = hashlib.md5(text.encode()).hexdigest()[:8]
        self._memory.preferences.set(key, text)
        console.print(f"[dim]Saved (key={key}): {text}[/dim]")

    def _handle_forget(self, key: str) -> None:
        """Delete a preference by key."""
        if self._memory is None:
            render_error("Memory system is disabled.")
            return
        if not key:
            render_error("Usage: /forget <key>")
            return
        self._memory.preferences.delete(key)
        console.print(f"[dim]Deleted preference: {key}[/dim]")

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
        deps = KubeAgentDeps(
            config=self.config,
            auto_approve=self.auto_approve,
            dry_run=self.dry_run,
            memory=self._memory,
        )

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
