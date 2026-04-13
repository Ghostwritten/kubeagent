"""KubeAgent Plugin System."""

from kubeagent.plugins.interface import (
    PluginInterface,
    PluginManifest,
    PluginPermissions,
    PluginType,
)

__all__ = ["PluginInterface", "PluginManifest", "PluginPermissions", "PluginType"]
