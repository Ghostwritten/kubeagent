"""Tests for Phase 07 — Prompt Engine + Policy."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kubeagent.agent.deps import KubeAgentDeps
from kubeagent.agent.policy import (
    PolicyDecision,
    build_impact_description,
    check_policy,
    get_risk_message,
    needs_double_confirmation,
)
from kubeagent.agent.prompt_engine import (
    build_cluster_context,
    build_preferences_section,
    build_system_prompt,
    load_kubeagent_md,
)
from kubeagent.config.settings import KubeAgentConfig, OutputConfig
from kubeagent.tools.registry import get_registry

# ---------------------------------------------------------------------------
# Prompt Engine tests
# ---------------------------------------------------------------------------


class TestBuildClusterContext:
    def test_with_all_info(self) -> None:
        ctx = build_cluster_context(cluster_name="prod", namespace="default", server="https://k8s.example.com")
        assert "prod" in ctx
        assert "default" in ctx
        assert "https://k8s.example.com" in ctx

    def test_no_cluster(self) -> None:
        assert build_cluster_context() == ""

    def test_cluster_only(self) -> None:
        ctx = build_cluster_context(cluster_name="dev")
        assert "dev" in ctx
        assert "namespace" not in ctx.lower()


class TestBuildPreferences:
    def test_default_config(self) -> None:
        config = KubeAgentConfig()
        prefs = build_preferences_section(config)
        assert "mixed" in prefs
        assert "claude" in prefs.lower() or "model" in prefs.lower()

    def test_custom_language(self) -> None:
        config = KubeAgentConfig(output=OutputConfig(language="zh"))
        prefs = build_preferences_section(config)
        assert "zh" in prefs


class TestLoadKubeagentMd:
    def test_explicit_path(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Rules\n- Always use namespace staging")
            f.flush()
            content = load_kubeagent_md(Path(f.name))
            assert content is not None
            assert "staging" in content
            Path(f.name).unlink()

    def test_missing_file(self) -> None:
        content = load_kubeagent_md(Path("/nonexistent/KUBEAGENT.md"))
        assert content is None

    def test_no_path_no_file(self) -> None:
        # When no path given and no KUBEAGENT.md in CWD or global, returns None
        content = load_kubeagent_md()
        # Could be None or content depending on environment
        assert content is None or isinstance(content, str)


class TestBuildSystemPrompt:
    def test_basic_prompt(self) -> None:
        config = KubeAgentConfig()
        prompt = build_system_prompt(config)
        assert "KubeAgent" in prompt
        assert "Preferences" in prompt

    def test_with_cluster_context(self) -> None:
        config = KubeAgentConfig()
        prompt = build_system_prompt(config, cluster_name="prod", namespace="default")
        assert "prod" in prompt
        assert "default" in prompt
        assert "Cluster" in prompt

    def test_with_kubeagent_md(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Project Rules\n- Always deploy to staging first")
            f.flush()
            config = KubeAgentConfig()
            prompt = build_system_prompt(config, kubeagent_md_path=Path(f.name))
            assert "staging" in prompt
            assert "KUBEAGENT.md" in prompt
            Path(f.name).unlink()


# ---------------------------------------------------------------------------
# Policy Engine tests
# ---------------------------------------------------------------------------


class TestPolicyDecision:
    def test_safe_tool_allowed(self) -> None:
        registry = get_registry()
        decision = check_policy("get_pods", registry)
        assert decision == PolicyDecision.ALLOW

    def test_sensitive_needs_confirm(self) -> None:
        registry = get_registry()
        decision = check_policy("scale_resource", registry)
        assert decision == PolicyDecision.CONFIRM

    def test_dangerous_needs_confirm(self) -> None:
        registry = get_registry()
        decision = check_policy("delete_resource", registry)
        assert decision == PolicyDecision.CONFIRM

    def test_dry_run_always_allowed(self) -> None:
        registry = get_registry()
        decision = check_policy("delete_resource", registry, dry_run=True)
        assert decision == PolicyDecision.ALLOW

    def test_auto_approve_skips_confirm(self) -> None:
        registry = get_registry()
        decision = check_policy("delete_resource", registry, auto_approve=True)
        assert decision == PolicyDecision.ALLOW

    def test_unknown_tool_denied(self) -> None:
        registry = get_registry()
        decision = check_policy("nonexistent_tool", registry)
        assert decision == PolicyDecision.DENY


class TestRiskMessage:
    def test_safe_no_risk(self) -> None:
        registry = get_registry()
        msg = get_risk_message("get_pods", registry)
        assert msg == ""

    def test_dangerous_has_warning(self) -> None:
        registry = get_registry()
        msg = get_risk_message("delete_resource", registry)
        assert "dangerous" in msg.lower() or "WARNING" in msg


class TestBuildImpactDescription:
    def test_delete_resource(self) -> None:
        registry = get_registry()
        desc = build_impact_description(
            "delete_resource",
            {"kind": "pod", "name": "nginx-123", "namespace": "default"},
            registry,
        )
        assert "nginx-123" in desc
        assert "delete" in desc.lower()

    def test_scale_resource(self) -> None:
        registry = get_registry()
        desc = build_impact_description(
            "scale_resource",
            {"kind": "deployment", "name": "web", "replicas": 5},
            registry,
        )
        assert "5" in desc
        assert "scale" in desc.lower()

    def test_drain_node(self) -> None:
        registry = get_registry()
        desc = build_impact_description(
            "drain_node", {"name": "node-1"}, registry
        )
        assert "drain" in desc.lower()
        assert "node-1" in desc

    def test_unknown_tool(self) -> None:
        registry = get_registry()
        desc = build_impact_description("nonexistent", {}, registry)
        assert "Unknown" in desc


class TestNeedsDoubleConfirmation:
    def test_drain_needs_double(self) -> None:
        registry = get_registry()
        assert needs_double_confirmation("drain_node", registry) is True

    def test_delete_no_double(self) -> None:
        registry = get_registry()
        assert needs_double_confirmation("delete_resource", registry) is False

    def test_safe_no_double(self) -> None:
        registry = get_registry()
        assert needs_double_confirmation("get_pods", registry) is False


# ---------------------------------------------------------------------------
# REPL command tests
# ---------------------------------------------------------------------------


class TestREPLPolicyCommands:
    def test_yes_toggle(self) -> None:
        from kubeagent.cli.repl import KubeAgentREPL

        repl = KubeAgentREPL(KubeAgentConfig())
        assert repl.auto_approve is False
        repl._handle_command("/yes")
        assert repl.auto_approve is True
        repl._handle_command("/yes")
        assert repl.auto_approve is False

    def test_dryrun_toggle(self) -> None:
        from kubeagent.cli.repl import KubeAgentREPL

        repl = KubeAgentREPL(KubeAgentConfig())
        assert repl.dry_run is False
        repl._handle_command("/dryrun")
        assert repl.dry_run is True
        repl._handle_command("/dryrun")
        assert repl.dry_run is False


# ---------------------------------------------------------------------------
# Deps integration tests
# ---------------------------------------------------------------------------


class TestKubeAgentDeps:
    def test_defaults(self) -> None:
        deps = KubeAgentDeps(config=KubeAgentConfig())
        assert deps.auto_approve is False
        assert deps.dry_run is False

    def test_custom_flags(self) -> None:
        deps = KubeAgentDeps(config=KubeAgentConfig(), auto_approve=True, dry_run=True)
        assert deps.auto_approve is True
        assert deps.dry_run is True


# ---------------------------------------------------------------------------
# Policy gate integration tests (_call_tool)
# ---------------------------------------------------------------------------


class TestCallToolPolicyGate:
    """Test that _call_tool respects policy decisions."""

    def _make_ctx(self, auto_approve: bool = False, dry_run: bool = False):
        """Create a mock RunContext with deps."""
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.deps = KubeAgentDeps(
            config=KubeAgentConfig(),
            auto_approve=auto_approve,
            dry_run=dry_run,
        )
        return ctx

    def test_safe_tool_executes(self) -> None:
        """Safe tools should execute without policy block."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.pods import GetPodsTool

        ctx = self._make_ctx()
        # Will fail to connect (no cluster), but the point is it's not blocked by policy
        result = _call_tool(GetPodsTool, ctx, namespace="default")
        # Should not contain "CONFIRMATION REQUIRED" or "DENIED"
        assert "CONFIRMATION REQUIRED" not in result
        assert "DENIED" not in result

    def test_dangerous_tool_blocked_without_approve(self) -> None:
        """Dangerous tools should be blocked when auto_approve is off."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.delete import DeleteResourceTool

        ctx = self._make_ctx(auto_approve=False)
        result = _call_tool(
            DeleteResourceTool, ctx, kind="pod", name="test", namespace="default"
        )
        assert "CONFIRMATION REQUIRED" in result

    def test_dangerous_tool_allowed_with_approve(self) -> None:
        """Dangerous tools should proceed when auto_approve is on."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.delete import DeleteResourceTool

        ctx = self._make_ctx(auto_approve=True)
        result = _call_tool(
            DeleteResourceTool, ctx, kind="pod", name="test", namespace="default"
        )
        # Should not be blocked — will fail to connect, but not a policy block
        assert "CONFIRMATION REQUIRED" not in result

    def test_sensitive_tool_blocked_without_approve(self) -> None:
        """Sensitive tools should be blocked when auto_approve is off."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.scale import ScaleResourceTool

        ctx = self._make_ctx(auto_approve=False)
        result = _call_tool(
            ScaleResourceTool,
            ctx,
            kind="deployment",
            name="web",
            namespace="default",
            replicas=3,
        )
        assert "CONFIRMATION REQUIRED" in result

    def test_dry_run_bypasses_policy(self) -> None:
        """Dry-run mode should bypass confirmation for dangerous tools."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.delete import DeleteResourceTool

        ctx = self._make_ctx(dry_run=True)
        result = _call_tool(
            DeleteResourceTool, ctx, kind="pod", name="test", namespace="default"
        )
        # dry_run=True makes check_policy return ALLOW, so no policy block
        assert "CONFIRMATION REQUIRED" not in result
        assert "DENIED" not in result
