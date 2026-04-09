"""Tests for CLI behavior."""

from click.testing import CliRunner

from kubeagent.cli.main import cli


def test_cli_version() -> None:
    """kubeagent --version outputs version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help() -> None:
    """kubeagent --help outputs usage with all commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "KubeAgent" in result.output
    assert "init" in result.output
    assert "doctor" in result.output
    assert "info" in result.output


def test_cli_info() -> None:
    """kubeagent info shows version and config."""
    runner = CliRunner()
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_init_help() -> None:
    """kubeagent init --help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "setup wizard" in result.output.lower()


def test_cli_doctor_help() -> None:
    """kubeagent doctor --help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "diagnostics" in result.output.lower()


def test_cli_doctor_runs() -> None:
    """kubeagent doctor runs and shows check results."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    # Should show at least one check indicator
    assert "✅" in result.output or "❌" in result.output
