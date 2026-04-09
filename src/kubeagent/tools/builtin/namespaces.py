"""Tool: get namespaces."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetNamespacesTool(BaseTool):
    name = "get_namespaces"
    description = "List all namespaces in the cluster."
    security_level = SecurityLevel.SAFE

    def execute(self, executor: PythonClientExecutor) -> list[dict]:
        ns_list = executor.list_namespaces()
        return [{"name": ns.name, "status": ns.status, "age": ns.age} for ns in ns_list]
