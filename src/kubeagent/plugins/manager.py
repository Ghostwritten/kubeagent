"""Plugin manager — discovers, loads, and manages plugin lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from kubeagent.plugins.interface import PluginInterface, PluginManifest, PluginType


class PluginState(StrEnum):
    """Lifecycle state of a plugin."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class LoadedPlugin:
    """A loaded plugin instance."""

    manifest: PluginManifest
    instance: PluginInterface
    state: PluginState = PluginState.DISCOVERED
    error: str | None = None


class PluginManager:
    """Manages all plugin lifecycle operations.

    Responsibilities:
    - Discover plugins from ~/.kubeagent/plugins/
    - Load/unload plugins
    - Enable/disable plugins
    - Track plugin state
    """

    def __init__(self, plugins_dir: Path | None = None) -> None:
        self._plugins_dir = plugins_dir or Path.home() / ".kubeagent" / "plugins"
        self._plugins: dict[str, LoadedPlugin] = {}
        self._discover_plugins()

    def _discover_plugins(self) -> None:
        """Auto-discover plugins from the plugins directory."""
        if not self._plugins_dir.exists():
            return

        for entry in self._plugins_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "plugin.yaml"
            if not manifest_path.exists():
                continue
            try:
                manifest = PluginManifest.from_file(manifest_path)
                self._plugins[manifest.name] = LoadedPlugin(
                    manifest=manifest,
                    instance=self._load_plugin_instance(manifest),
                    state=PluginState.LOADED,
                )
            except Exception as e:
                # Record plugin with error state
                try:
                    manifest = PluginManifest.from_file(manifest_path)
                    self._plugins[manifest.name] = LoadedPlugin(
                        manifest=manifest,
                        instance=self._create_dummy_instance(manifest),
                        state=PluginState.ERROR,
                        error=str(e),
                    )
                except Exception:
                    pass  # Skip completely broken plugins

    def _load_plugin_instance(self, manifest: PluginManifest) -> PluginInterface:
        """Load a plugin instance from its entry point.

        Entry point format: "module:ClassName"
        """
        module_name, class_name = manifest.entry_point.split(":", 1)

        import importlib

        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        instance = cls()
        return instance

    def _create_dummy_instance(self, manifest: PluginManifest) -> PluginInterface:
        """Create a minimal instance for error tracking plugins."""

        class DummyPlugin(PluginInterface):
            def initialize(self) -> None:
                pass

            def shutdown(self) -> None:
                pass

        return DummyPlugin()

    def install_plugin(self, plugin_dir: Path) -> None:
        """Install a plugin from a directory.

        Copies the plugin directory into the plugins directory.
        """
        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"plugin.yaml not found in {plugin_dir}")

        manifest = PluginManifest.from_file(manifest_path)
        dest = self._plugins_dir / manifest.name

        # If source is already inside the plugins directory, just load it
        if plugin_dir.resolve() == dest.resolve():
            if manifest.name not in self._plugins:
                self._plugins[manifest.name] = LoadedPlugin(
                    manifest=manifest,
                    instance=self._load_plugin_instance(manifest),
                    state=PluginState.LOADED,
                )
            return

        if dest.exists():
            raise FileExistsError(f"Plugin '{manifest.name}' already installed")

        import shutil

        shutil.copytree(plugin_dir, dest)
        # Reload to pick up new plugin
        self._plugins[manifest.name] = LoadedPlugin(
            manifest=manifest,
            instance=self._load_plugin_instance(manifest),
            state=PluginState.LOADED,
        )

    def remove_plugin(self, name: str) -> None:
        """Remove an installed plugin."""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")

        plugin_path = self._plugins_dir / name
        if plugin_path.exists():
            import shutil

            shutil.rmtree(plugin_path)

        del self._plugins[name]

    def enable_plugin(self, name: str) -> None:
        """Enable a plugin."""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")
        plugin = self._plugins[name]
        plugin.state = PluginState.ENABLED
        try:
            plugin.instance.initialize()
        except Exception as e:
            plugin.state = PluginState.ERROR
            plugin.error = str(e)

    def disable_plugin(self, name: str) -> None:
        """Disable a plugin."""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")
        plugin = self._plugins[name]
        plugin.state = PluginState.DISABLED
        try:
            plugin.instance.shutdown()
        except Exception:
            pass

    def get_plugin(self, name: str) -> LoadedPlugin | None:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self, type_filter: PluginType | None = None) -> list[str]:
        """List all plugin names, optionally filtered by type."""
        names = []
        for name, plugin in self._plugins.items():
            if type_filter and plugin.manifest.type != type_filter:
                continue
            names.append(name)
        return names

    def list_tools_from_plugins(self) -> list[str]:
        """List tool names contributed by tool plugins."""
        names = []
        for plugin in self._plugins.values():
            if plugin.manifest.type == PluginType.TOOL and plugin.state in (
                PluginState.LOADED,
                PluginState.ENABLED,
            ):
                names.append(plugin.manifest.name)
        return names

    def list_skills_from_plugins(self) -> list[str]:
        """List skill names contributed by skill plugins."""
        names = []
        for plugin in self._plugins.values():
            if plugin.manifest.type == PluginType.SKILL and plugin.state in (
                PluginState.LOADED,
                PluginState.ENABLED,
            ):
                names.append(plugin.manifest.name)
        return names
