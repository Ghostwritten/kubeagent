"""Tool: get nodes."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetNodesTool(BaseTool):
    name = "get_nodes"
    description = "List all nodes with status, roles, version, and allocatable resources."
    security_level = SecurityLevel.SAFE

    def execute(self, executor: PythonClientExecutor) -> list[dict]:
        nodes = executor.list_nodes()
        return [
            {
                "name": n.name,
                "status": n.status_text,
                "roles": ",".join(n.roles) if n.roles else "<none>",
                "version": n.version,
                "age": n.age,
                "cpu_allocatable": n.cpu_allocatable,
                "memory_allocatable": n.memory_allocatable,
            }
            for n in nodes
        ]
