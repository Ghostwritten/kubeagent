"""Tool: get configmaps."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetConfigMapsTool(BaseTool):
    name = "get_configmaps"
    description = "List configmaps in a namespace."
    security_level = SecurityLevel.SAFE

    def execute(self, executor: PythonClientExecutor, namespace: str = "default") -> list[dict]:
        cms = executor.list_configmaps(namespace=namespace)
        return [{"name": cm.name, "namespace": cm.namespace, "age": cm.age} for cm in cms]
