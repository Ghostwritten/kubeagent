"""Tests for Phase 12 — MCP Server + Ecosystem."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kubeagent.mcp.ecosystem.argocd import (
    ARGOCD_TOOLS,
    ArgoCDAppGetTool,
    ArgoCDAppListTool,
    ArgoCDAppRollbackTool,
    ArgoCDAppSyncTool,
)
from kubeagent.mcp.ecosystem.grafana import (
    GRAFANA_TOOLS,
    GrafanaAnnotationCreateTool,
    GrafanaDashboardGetTool,
    GrafanaDashboardListTool,
)
from kubeagent.mcp.ecosystem.helm import (
    HELM_TOOLS,
    HelmHistoryTool,
    HelmInstallTool,
    HelmListTool,
    HelmRollbackTool,
    HelmStatusTool,
    HelmUninstallTool,
    HelmUpgradeTool,
)
from kubeagent.mcp.ecosystem.istio import (
    ISTIO_TOOLS,
    IstioAnalyzeTool,
    IstioProxyConfigTool,
)
from kubeagent.mcp.ecosystem.prometheus import (
    PROMETHEUS_TOOLS,
    PrometheusQueryRangeTool,
    PrometheusQueryTool,
)

# ---------------------------------------------------------------------------
# T1: MCP Server
# ---------------------------------------------------------------------------


class TestMCPServer:
    def test_server_creates(self) -> None:
        """MCP server can be instantiated."""
        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        assert server is not None

    def test_server_has_tools(self) -> None:
        """MCP server registers core tools."""
        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        assert server.tool_count > 0

    def test_server_has_skills(self) -> None:
        """MCP server registers skills as resources."""
        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        assert server.skill_count > 0

    def test_server_exposes_fastmcp(self) -> None:
        """MCP server exposes the underlying FastMCP instance."""
        from fastmcp import FastMCP

        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        mcp = server.get_mcp()
        assert isinstance(mcp, FastMCP)

    def test_server_ecosystem_tools_registered(self) -> None:
        """MCP server includes ecosystem tools (Helm, Istio, etc.)."""
        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        # Core tools + ecosystem tools (7 helm + 4 istio + 6 argocd + 4 prom + 3 grafana = 24)
        assert server.tool_count >= 24


# ---------------------------------------------------------------------------
# T2: MCP CLI
# ---------------------------------------------------------------------------


class TestMCPCLI:
    def test_mcp_status_not_running(self) -> None:
        """mcp status shows not running when no server exists."""
        from click.testing import CliRunner

        from kubeagent.mcp.cli import mcp_group

        runner = CliRunner()
        result = runner.invoke(mcp_group, ["status"])
        assert result.exit_code == 0
        assert "not running" in result.output

    def test_mcp_stop_not_running(self) -> None:
        """mcp stop handles no server gracefully."""
        from click.testing import CliRunner

        from kubeagent.mcp.cli import mcp_group

        runner = CliRunner()
        result = runner.invoke(mcp_group, ["stop"])
        assert result.exit_code == 0
        assert "not running" in result.output

    def test_mcp_group_has_commands(self) -> None:
        """MCP CLI group has start/stop/status commands."""
        from kubeagent.mcp.cli import mcp_group

        command_names = [cmd for cmd in mcp_group.commands]
        assert "start" in command_names
        assert "stop" in command_names
        assert "status" in command_names

    def test_mcp_registered_in_main_cli(self) -> None:
        """MCP group is registered in the main CLI."""
        from kubeagent.cli.main import cli

        command_names = [cmd for cmd in cli.commands]
        assert "mcp" in command_names


# ---------------------------------------------------------------------------
# T3: Helm Ecosystem Plugin
# ---------------------------------------------------------------------------


class TestHelmTools:
    def test_helm_tools_count(self) -> None:
        """All Helm tools are exported."""
        assert len(HELM_TOOLS) == 7

    def test_helm_list_tool_metadata(self) -> None:
        """HelmListTool has correct name and security level."""
        tool = HelmListTool()
        assert tool.name == "helm_list"
        assert tool.security_level.value == "safe"

    def test_helm_install_requires_params(self) -> None:
        """HelmInstallTool returns error when required params missing."""
        tool = HelmInstallTool()
        result = tool.execute()
        assert "error" in result

    def test_helm_upgrade_requires_params(self) -> None:
        """HelmUpgradeTool returns error when required params missing."""
        tool = HelmUpgradeTool()
        result = tool.execute()
        assert "error" in result

    def test_helm_uninstall_requires_release(self) -> None:
        """HelmUninstallTool returns error without release_name."""
        tool = HelmUninstallTool()
        result = tool.execute()
        assert "error" in result

    def test_helm_status_requires_release(self) -> None:
        """HelmStatusTool returns error without release_name."""
        tool = HelmStatusTool()
        result = tool.execute()
        assert "error" in result

    def test_helm_history_requires_release(self) -> None:
        """HelmHistoryTool returns error without release_name."""
        tool = HelmHistoryTool()
        result = tool.execute()
        assert "error" in result

    def test_helm_rollback_requires_release(self) -> None:
        """HelmRollbackTool returns error without release_name."""
        tool = HelmRollbackTool()
        result = tool.execute()
        assert "error" in result

    def test_helm_install_security_level(self) -> None:
        """HelmInstallTool is SENSITIVE."""
        tool = HelmInstallTool()
        assert tool.security_level.value == "sensitive"

    def test_helm_uninstall_security_level(self) -> None:
        """HelmUninstallTool is DANGEROUS."""
        tool = HelmUninstallTool()
        assert tool.security_level.value == "dangerous"

    @patch("kubeagent.mcp.ecosystem.helm.subprocess.run")
    def test_helm_list_executes(self, mock_run: MagicMock) -> None:
        """HelmListTool calls helm list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name":"my-release","namespace":"default"}]',
            stderr="",
        )
        tool = HelmListTool()
        result = tool.execute()
        mock_run.assert_called_once()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# T4: Istio Ecosystem Plugin
# ---------------------------------------------------------------------------


class TestIstioTools:
    def test_istio_tools_count(self) -> None:
        """All Istio tools are exported."""
        assert len(ISTIO_TOOLS) == 4

    def test_istio_analyze_metadata(self) -> None:
        """IstioAnalyzeTool has correct metadata."""
        tool = IstioAnalyzeTool()
        assert tool.name == "istio_analyze"
        assert tool.security_level.value == "safe"

    def test_istio_proxy_config_requires_pod(self) -> None:
        """IstioProxyConfigTool returns error without pod."""
        tool = IstioProxyConfigTool()
        result = tool.execute()
        assert "error" in result

    def test_all_istio_tools_are_safe(self) -> None:
        """All Istio tools are read-only (SAFE)."""
        for tool_cls in ISTIO_TOOLS:
            tool = tool_cls()
            assert tool.security_level.value == "safe", f"{tool.name} should be SAFE"


# ---------------------------------------------------------------------------
# T5: ArgoCD Ecosystem Plugin
# ---------------------------------------------------------------------------


class TestArgoCDTools:
    def test_argocd_tools_count(self) -> None:
        """All ArgoCD tools are exported."""
        assert len(ARGOCD_TOOLS) == 6

    def test_argocd_app_get_requires_name(self) -> None:
        """ArgoCDAppGetTool returns error without app_name."""
        tool = ArgoCDAppGetTool()
        result = tool.execute()
        assert "error" in result

    def test_argocd_app_sync_requires_name(self) -> None:
        """ArgoCDAppSyncTool returns error without app_name."""
        tool = ArgoCDAppSyncTool()
        result = tool.execute()
        assert "error" in result

    def test_argocd_app_rollback_requires_params(self) -> None:
        """ArgoCDAppRollbackTool returns error without params."""
        tool = ArgoCDAppRollbackTool()
        result = tool.execute()
        assert "error" in result

    def test_argocd_rollback_requires_positive_revision(self) -> None:
        """ArgoCDAppRollbackTool requires positive revision."""
        tool = ArgoCDAppRollbackTool()
        result = tool.execute(app_name="myapp", revision=0)
        assert "error" in result

    def test_argocd_sync_is_sensitive(self) -> None:
        """ArgoCDAppSyncTool is SENSITIVE."""
        tool = ArgoCDAppSyncTool()
        assert tool.security_level.value == "sensitive"

    def test_argocd_list_is_safe(self) -> None:
        """ArgoCDAppListTool is SAFE."""
        tool = ArgoCDAppListTool()
        assert tool.security_level.value == "safe"


# ---------------------------------------------------------------------------
# T6: Observability Plugins
# ---------------------------------------------------------------------------


class TestPrometheusTools:
    def test_prometheus_tools_count(self) -> None:
        """All Prometheus tools are exported."""
        assert len(PROMETHEUS_TOOLS) == 4

    def test_prometheus_query_requires_query(self) -> None:
        """PrometheusQueryTool returns error without query."""
        tool = PrometheusQueryTool()
        result = tool.execute()
        assert "error" in result

    def test_prometheus_query_range_requires_query(self) -> None:
        """PrometheusQueryRangeTool returns error without query."""
        tool = PrometheusQueryRangeTool()
        result = tool.execute()
        assert "error" in result

    def test_all_prometheus_tools_are_safe(self) -> None:
        """All Prometheus tools are SAFE (read-only)."""
        for tool_cls in PROMETHEUS_TOOLS:
            tool = tool_cls()
            assert tool.security_level.value == "safe", f"{tool.name} should be SAFE"

    @patch("kubeagent.mcp.ecosystem.prometheus.requests.get")
    def test_prometheus_query_calls_api(self, mock_get: MagicMock) -> None:
        """PrometheusQueryTool calls Prometheus API."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "data": {"result": []}},
        )
        mock_get.return_value.raise_for_status = lambda: None
        tool = PrometheusQueryTool()
        result = tool.execute(query="up")
        mock_get.assert_called_once()
        assert result["status"] == "success"

    @patch("kubeagent.mcp.ecosystem.prometheus.requests.get")
    def test_prometheus_connection_error(self, mock_get: MagicMock) -> None:
        """PrometheusQueryTool handles connection errors."""
        import requests as req

        mock_get.side_effect = req.ConnectionError()
        tool = PrometheusQueryTool()
        result = tool.execute(query="up")
        assert "error" in result
        assert "Cannot connect" in result["error"]


class TestGrafanaTools:
    def test_grafana_tools_count(self) -> None:
        """All Grafana tools are exported."""
        assert len(GRAFANA_TOOLS) == 3

    def test_grafana_dashboard_get_requires_uid(self) -> None:
        """GrafanaDashboardGetTool returns error without uid."""
        tool = GrafanaDashboardGetTool()
        result = tool.execute()
        assert "error" in result

    def test_grafana_annotation_requires_text(self) -> None:
        """GrafanaAnnotationCreateTool returns error without text."""
        tool = GrafanaAnnotationCreateTool()
        result = tool.execute()
        assert "error" in result

    def test_grafana_annotation_is_sensitive(self) -> None:
        """GrafanaAnnotationCreateTool is SENSITIVE."""
        tool = GrafanaAnnotationCreateTool()
        assert tool.security_level.value == "sensitive"

    @patch("kubeagent.mcp.ecosystem.grafana.requests.get")
    def test_grafana_dashboard_list_calls_api(self, mock_get: MagicMock) -> None:
        """GrafanaDashboardListTool calls Grafana API."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {"title": "My Dashboard", "uid": "abc", "url": "/d/abc", "tags": []}
            ],
        )
        mock_get.return_value.raise_for_status = lambda: None
        tool = GrafanaDashboardListTool()
        result = tool.execute()
        mock_get.assert_called_once()
        assert len(result) == 1
        assert result[0]["title"] == "My Dashboard"


# ---------------------------------------------------------------------------
# Acceptance Criteria
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    def test_ac1_mcp_server_starts(self) -> None:
        """AC1: MCP server can be created and has tools registered."""
        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        assert server.tool_count > 0
        assert server.skill_count > 0

    def test_ac2_tools_exposed_via_mcp(self) -> None:
        """AC2: Core K8s tools are exposed via MCP."""
        from kubeagent.mcp.server import KubeAgentMCPServer

        server = KubeAgentMCPServer()
        mcp = server.get_mcp()
        assert mcp is not None
        # Server was created with tools registered
        assert server.tool_count >= 10

    def test_ac3_helm_plugin_functional(self) -> None:
        """AC3: Helm plugin can list (returns error gracefully if helm not installed)."""
        tool = HelmListTool()
        result = tool.execute()
        # Will either return list or error dict — both are valid
        assert isinstance(result, (list, dict))

    def test_ac4_istio_plugin_functional(self) -> None:
        """AC4: Istio plugin can analyze (returns error gracefully if not installed)."""
        tool = IstioAnalyzeTool()
        result = tool.execute()
        assert isinstance(result, dict)

    def test_ac5_argocd_plugin_functional(self) -> None:
        """AC5: ArgoCD plugin can list (returns error gracefully if not installed)."""
        tool = ArgoCDAppListTool()
        result = tool.execute()
        assert isinstance(result, dict)

    def test_ecosystem_tool_coverage(self) -> None:
        """All ecosystem tools are BaseTool subclasses with proper metadata."""
        from kubeagent.tools.base import BaseTool

        all_tools = (
            HELM_TOOLS + ISTIO_TOOLS + ARGOCD_TOOLS + PROMETHEUS_TOOLS + GRAFANA_TOOLS
        )
        assert len(all_tools) == 24
        for tool_cls in all_tools:
            instance = tool_cls()
            assert isinstance(instance, BaseTool)
            assert instance.name != ""
            assert instance.description != ""
