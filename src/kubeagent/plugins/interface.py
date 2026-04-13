"""Plugin interface — plugin manifest and type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yaml


class PluginType(StrEnum):
    """Type of plugin."""

    TOOL = "tool"  # Adds tools to the agent
    SKILL = "skill"  # Adds skills
    POLICY = "policy"  # Adds policy rules


@dataclass
class PluginPermissions:
    """Permissions declared by a plugin."""

    allowed_tools: list[str] = field(default_factory=list)
    allowed_namespaces: list[str] = field(default_factory=list)
    allowed_clusters: list[str] = field(default_factory=list)

    def allows_tool(self, tool_name: str) -> bool:
        """Check if plugin is allowed to use a tool."""
        if not self.allowed_tools:
            return True  # Empty = all allowed
        return tool_name in self.allowed_tools

    def allows_namespace(self, namespace: str) -> bool:
        """Check if plugin is allowed to access a namespace."""
        if not self.allowed_namespaces:
            return True  # Empty = all allowed
        return namespace in self.allowed_namespaces


@dataclass
class PluginManifest:
    """Plugin manifest — plugin.yaml metadata."""

    name: str
    version: str
    type: PluginType
    entry_point: str  # "module:ClassName" or "module:function"
    description: str = ""
    author: str = ""
    permissions: PluginPermissions = field(default_factory=PluginPermissions)
    dependencies: list[str] = field(default_factory=list)
    min_kubeagent_version: str = "0.1.0"

    @classmethod
    def from_file(cls, path: Path) -> PluginManifest:
        """Load manifest from a plugin.yaml file."""
        data = yaml.safe_load(path.read_text()) or {}
        perms_data = data.pop("permissions", {})
        permissions = PluginPermissions(**perms_data) if perms_data else PluginPermissions()
        data["permissions"] = permissions
        if "type" in data:
            data["type"] = PluginType(data["type"])
        return cls(**data)

    def to_dict(self) -> dict:
        """Serialize manifest to dict."""
        type_val = self.type.value if isinstance(self.type, PluginType) else self.type
        d = {
            "name": self.name,
            "version": self.version,
            "type": type_val,
            "entry_point": self.entry_point,
            "description": self.description,
            "author": self.author,
            "permissions": {
                "allowed_tools": self.permissions.allowed_tools,
                "allowed_namespaces": self.permissions.allowed_namespaces,
                "allowed_clusters": self.permissions.allowed_clusters,
            },
            "dependencies": self.dependencies,
            "min_kubeagent_version": self.min_kubeagent_version,
        }
        return d


class PluginInterface:
    """Base class for all KubeAgent plugins.

    Plugins implement this interface to be loadable by PluginManager.
    """

    manifest: PluginManifest

    def initialize(self) -> None:
        """Called when plugin is loaded. Do any setup here."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Called when plugin is unloaded. Do any cleanup here."""
        raise NotImplementedError
