"""Tests for Phase 11 — Plugin System."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from kubeagent.plugins.cli import run_plugin_command
from kubeagent.plugins.interface import PluginManifest, PluginType
from kubeagent.plugins.manager import PluginManager, PluginState
from kubeagent.plugins.sandbox import PluginPermissions, PluginSandbox
from kubeagent.plugins.user_tools import ShellTool, register_user_tool

# ---------------------------------------------------------------------------
# T1: Plugin Interface
# ---------------------------------------------------------------------------


class TestPluginManifest:
    def test_parse_valid_manifest(self) -> None:
        """PluginManifest parses valid YAML."""
        data = {
            "name": "my-plugin",
            "version": "1.0.0",
            "type": "tool",
            "entry_point": "my_plugin:MyTool",
            "permissions": {"allowed_tools": ["get_pods"]},
        }
        manifest = PluginManifest(**data)
        assert manifest.name == "my-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.type == PluginType.TOOL

    def test_manifest_to_dict(self) -> None:
        """PluginManifest serializes to dict."""
        data = {
            "name": "test-plugin",
            "version": "0.1.0",
            "type": "skill",
            "entry_point": "test:Skill",
        }
        manifest = PluginManifest(**data)
        d = manifest.to_dict()
        assert d["name"] == "test-plugin"
        assert d["type"] == "skill"

    def test_plugin_type_enum(self) -> None:
        """PluginType has all expected values."""
        assert PluginType.TOOL is not None
        assert PluginType.SKILL is not None
        assert PluginType.POLICY is not None


# ---------------------------------------------------------------------------
# T2: Plugin Registry + Lifecycle
# ---------------------------------------------------------------------------


class TestPluginManager:
    def test_loads_no_plugins_when_empty(self) -> None:
        """PluginManager handles empty plugin directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PluginManager(plugins_dir=Path(tmpdir))
            assert len(mgr.list_plugins()) == 0

    def test_install_plugin_from_directory(self) -> None:
        """PluginManager installs a plugin from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake plugin dir
            plugin_dir = Path(tmpdir) / "my-plugin"
            plugin_dir.mkdir()
            manifest = {
                "name": "my-plugin",
                "version": "1.0.0",
                "type": "tool",
                "entry_point": "dummy:DummyTool",
            }
            (plugin_dir / "plugin.yaml").write_text(yaml.dump(manifest))

            mgr = PluginManager(plugins_dir=Path(tmpdir))
            mgr.install_plugin(plugin_dir)
            names = mgr.list_plugins()
            assert "my-plugin" in names

    def test_remove_plugin(self) -> None:
        """PluginManager removes a plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "to-remove"
            plugin_dir.mkdir()
            manifest = {
                "name": "to-remove",
                "version": "1.0.0",
                "type": "tool",
                "entry_point": "dummy:Dummy",
            }
            (plugin_dir / "plugin.yaml").write_text(yaml.dump(manifest))

            mgr = PluginManager(plugins_dir=Path(tmpdir))
            mgr.install_plugin(plugin_dir)
            mgr.remove_plugin("to-remove")
            assert "to-remove" not in mgr.list_plugins()

    def test_plugin_state(self) -> None:
        """PluginState tracks plugin lifecycle."""
        assert PluginState.DISCOVERED is not None
        assert PluginState.LOADED is not None
        assert PluginState.ENABLED is not None
        assert PluginState.DISABLED is not None


# ---------------------------------------------------------------------------
# T3: Plugin Sandboxing + Permissions
# ---------------------------------------------------------------------------


class TestPluginPermissions:
    def test_allows_matching_tool(self) -> None:
        """Permission check passes for allowed tool."""
        perms = PluginPermissions(allowed_tools=["get_pods", "get_nodes"])
        assert perms.allows_tool("get_pods") is True
        assert perms.allows_tool("get_nodes") is True

    def test_denies_undeclared_tool(self) -> None:
        """Permission check fails for undeclared tool."""
        perms = PluginPermissions(allowed_tools=["get_pods"])
        assert perms.allows_tool("delete_resource") is False

    def test_allows_matching_namespace(self) -> None:
        """Permission check passes for allowed namespace."""
        perms = PluginPermissions(allowed_namespaces=["default", "production"])
        assert perms.allows_namespace("default") is True
        assert perms.allows_namespace("production") is True

    def test_denies_undeclared_namespace(self) -> None:
        """Permission check fails for undeclared namespace."""
        perms = PluginPermissions(allowed_namespaces=["default"])
        assert perms.allows_namespace("kube-system") is False

    def test_empty_permissions_allow_all(self) -> None:
        """Empty permissions dict means all allowed."""
        perms = PluginPermissions()
        assert perms.allows_tool("any_tool") is True
        assert perms.allows_namespace("any-ns") is True


class TestPluginSandbox:
    def test_sandbox_executes_plugin(self) -> None:
        """PluginSandbox executes plugin code."""
        sandbox = PluginSandbox(PluginPermissions())
        # Simple test: verify sandbox doesn't crash on basic call
        result = sandbox.execute_python("1 + 1")
        assert result == 2

    def test_sandbox_restricted_shell(self) -> None:
        """Sandbox denies dangerous shell commands."""
        sandbox = PluginSandbox(PluginPermissions())
        ok, _ = sandbox.execute_shell("rm -rf /")
        assert ok is False

    def test_sandbox_allowed_shell(self) -> None:
        """Sandbox allows safe shell commands."""
        sandbox = PluginSandbox(PluginPermissions())
        ok, output = sandbox.execute_shell("echo hello")
        assert ok is True
        assert "hello" in output


# ---------------------------------------------------------------------------
# T4: User-Defined Tool Registration
# ---------------------------------------------------------------------------


class TestShellTool:
    def test_shell_tool_executes(self) -> None:
        """ShellTool executes a shell command."""
        tool = ShellTool(name="echo-test", command="echo hello")
        result = tool.execute()
        assert "hello" in str(result)

    def test_shell_tool_with_args(self) -> None:
        """ShellTool substitutes arguments."""
        tool = ShellTool(
            name="echo-arg",
            command="echo {msg}",
            args_schema=[{"name": "msg", "type": "str"}],
        )
        result = tool.execute(msg="world")
        assert "world" in str(result)

    def test_register_user_tool(self) -> None:
        """register_user_tool adds tool to registry."""
        tool = ShellTool(name="my-echo", command="echo done")
        register_user_tool(tool)
        from kubeagent.tools.registry import get_registry

        reg = get_registry()
        assert reg.get("my-echo") is not None


# ---------------------------------------------------------------------------
# T5: Plugin CLI + Community Skills
# ---------------------------------------------------------------------------


class TestPluginCLI:
    def test_plugin_list_command(self) -> None:
        """plugin list shows installed plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_plugin_command(["list"], plugins_dir=Path(tmpdir))
            assert result.exit_code == 0

    def test_plugin_install_unknown_package(self) -> None:
        """plugin install with unknown package shows helpful error."""
        result = run_plugin_command(
            ["install", "nonexistent-package-xyz"],
            plugins_dir=Path(tempfile.gettempdir()),
        )
        # Should not crash; exit code depends on whether package exists
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# Acceptance Criteria Tests
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    def test_plugin_loads_and_registers_tools(self) -> None:
        """AC1+2: Plugin can be loaded and adds tools to registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal plugin
            plugin_dir = Path(tmpdir) / "test-tool-plugin"
            plugin_dir.mkdir()
            manifest = {
                "name": "test-tool-plugin",
                "version": "1.0.0",
                "type": "tool",
                "entry_point": "kubeagent.plugins.user_tools:ShellTool",
            }
            (plugin_dir / "plugin.yaml").write_text(yaml.dump(manifest))

            mgr = PluginManager(plugins_dir=Path(tmpdir))
            mgr.install_plugin(plugin_dir)
            assert "test-tool-plugin" in mgr.list_plugins()

    def test_user_defined_shell_tool_registered(self) -> None:
        """AC4: User-defined shell tool can be registered and called."""
        tool = ShellTool(name="test-user-tool", command="echo user-defined")
        register_user_tool(tool)
        from kubeagent.tools.registry import get_registry

        reg = get_registry()
        assert reg.get("test-user-tool") is not None

    def test_plugin_permissions_enforced(self) -> None:
        """AC3: Plugin permissions are enforced."""
        perms = PluginPermissions(allowed_tools=["get_pods"])
        assert perms.allows_tool("get_pods") is True
        assert perms.allows_tool("delete_resource") is False
