"""Tool: cordon/uncordon/drain nodes."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class CordonNodeTool(BaseTool):
    name = "cordon_node"
    description = "Mark a node as unschedulable (no new pods)."
    security_level = SecurityLevel.DANGEROUS

    def execute(self, executor: PythonClientExecutor, name: str) -> dict[str, Any]:
        return executor.cordon_node(name=name)


class UncordonNodeTool(BaseTool):
    name = "uncordon_node"
    description = "Mark a node as schedulable again."
    security_level = SecurityLevel.SENSITIVE

    def execute(self, executor: PythonClientExecutor, name: str) -> dict[str, Any]:
        return executor.uncordon_node(name=name)


class DrainNodeTool(BaseTool):
    name = "drain_node"
    description = "Drain a node: cordon + evict all non-daemonset pods."
    security_level = SecurityLevel.DANGEROUS

    def execute(
        self,
        executor: PythonClientExecutor,
        name: str,
        force: bool = False,
    ) -> dict[str, Any]:
        return executor.drain_node(name=name, force=force)
