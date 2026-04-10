"""Tests for Phase 06 — Interactive CLI."""

from __future__ import annotations

from kubeagent.cli.output import (
    STYLE_ERROR,
    STYLE_SUCCESS,
    render_error,
    render_help,
    render_success,
    render_table,
    render_welcome,
)
from kubeagent.cli.repl import KubeAgentREPL
from kubeagent.config.settings import KubeAgentConfig

# ---------------------------------------------------------------------------
# Output rendering tests
# ---------------------------------------------------------------------------


class TestRenderOutput:
    def test_render_error(self) -> None:
        """render_error should not crash."""
        render_error("test error")

    def test_render_success(self) -> None:
        """render_success should not crash."""
        render_success("test success")

    def test_render_welcome(self) -> None:
        """render_welcome should not crash."""
        render_welcome("0.1.0", cluster="test-cluster")

    def test_render_welcome_no_cluster(self) -> None:
        """render_welcome without cluster should not crash."""
        render_welcome("0.1.0")

    def test_render_help(self) -> None:
        """render_help should not crash."""
        render_help()

    def test_render_table(self) -> None:
        """render_table should render a table."""
        render_table(
            title="Pods",
            columns=["Name", "Status"],
            rows=[["nginx", "Running"], ["redis", "Pending"]],
        )


class TestStyleConstants:
    def test_error_style(self) -> None:
        assert "red" in STYLE_ERROR

    def test_success_style(self) -> None:
        assert "green" in STYLE_SUCCESS


# ---------------------------------------------------------------------------
# REPL tests
# ---------------------------------------------------------------------------


class TestKubeAgentREPL:
    def test_init_defaults(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        assert repl.config is config
        assert repl.history == []
        assert repl._cluster_name is None

    def test_build_prompt(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        repl._cluster_name = "my-cluster"
        prompt = repl._build_prompt()
        assert "my-cluster" in prompt

    def test_build_prompt_no_cluster(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        prompt = repl._build_prompt()
        assert "no-cluster" in prompt

    def test_handle_command_exit(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        result = repl._handle_command("/exit")
        assert result == "exit"

    def test_handle_command_quit(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        result = repl._handle_command("/quit")
        assert result == "exit"

    def test_handle_command_q(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        result = repl._handle_command("/q")
        assert result == "exit"

    def test_handle_command_clear(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        repl.history = ["some", "history"]  # type: ignore[list-item]
        result = repl._handle_command("/clear")
        assert result is None
        assert repl.history == []

    def test_handle_command_help(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        result = repl._handle_command("/help")
        assert result is None

    def test_handle_command_model(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        result = repl._handle_command("/model")
        assert result is None

    def test_handle_command_unknown(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        result = repl._handle_command("/unknown")
        assert result is None

    def test_handle_shell(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        repl._handle_shell("echo hello")

    def test_handle_shell_empty(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        repl._handle_shell("")

    def test_handle_shell_timeout(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        repl._handle_shell("sleep 60")

    def test_init_agent(self) -> None:
        config = KubeAgentConfig()
        repl = KubeAgentREPL(config)
        assert repl._agent is None
        repl._init_agent()
        assert repl._agent is not None


# ---------------------------------------------------------------------------
# CLI smoke test (REPL not started, just command parsing)
# ---------------------------------------------------------------------------


class TestCLISmoke:
    def test_cli_version_still_works(self) -> None:
        from click.testing import CliRunner

        from kubeagent.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help_still_works(self) -> None:
        from click.testing import CliRunner

        from kubeagent.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "KubeAgent" in result.output
