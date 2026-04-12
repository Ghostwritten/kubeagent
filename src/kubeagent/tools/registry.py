"""Tool registry for KubeAgent."""

from __future__ import annotations

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.base import BaseTool


class ToolRegistry:
    """Central registry for all KubeAgent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, type[BaseTool]] = {}

    def register(self, tool_class: type[BaseTool]) -> None:
        """Register a tool class or instance.

        Accepts either a class (type) or an already-instantiated tool.
        """
        if isinstance(tool_class, BaseTool):
            # Already an instance — wrap it in a factory lambda
            instance = tool_class
            if not instance.name:
                raise ValueError(f"Tool has no name")
            self._tools[instance.name] = lambda: instance  # type: ignore[assignment]
        else:
            instance = tool_class()
            if not instance.name:
                msg = f"Tool {tool_class.__name__} has no name"
                raise ValueError(msg)
            self._tools[instance.name] = tool_class

    def get(self, name: str) -> type[BaseTool] | None:
        """Get a tool class by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        """List all registered tools."""
        return [tool_class().to_dict() for tool_class in self._tools.values()]

    def filter_by_security(self, level: SecurityLevel) -> list[type[BaseTool]]:
        """Get all tools matching a security level."""
        return [tc for tc in self._tools.values() if tc().security_level == level]

    def __len__(self) -> int:
        return len(self._tools)


# Global registry instance
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry, creating it if needed."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _discover_tools(_registry)
    return _registry


def _discover_tools(registry: ToolRegistry) -> None:
    """Auto-discover and register all built-in tools."""
    from kubeagent.tools.builtin import (
        apply,
        configmaps,
        delete,
        describe,
        events,
        kubectl,
        logs,
        namespaces,
        nodes,
        nodes_ops,
        pods,
        restart,
        scale,
        services,
    )

    for module in [
        pods,
        nodes,
        namespaces,
        services,
        configmaps,
        describe,
        events,
        logs,
        apply,
        delete,
        scale,
        restart,
        nodes_ops,
        kubectl,
    ]:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseTool) and attr is not BaseTool:
                registry.register(attr)
