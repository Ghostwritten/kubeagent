"""Tool: get pods."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetPodsTool(BaseTool):
    name = "get_pods"
    description = "List pods with status, ready, restarts, node, and age."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        executor: PythonClientExecutor,
        namespace: str = "",
        label_selector: dict[str, str] | None = None,
    ) -> list[dict]:
        pods = executor.list_pods(namespace=namespace, label_selector=label_selector)
        return [
            {
                "name": p.name,
                "namespace": p.namespace,
                "status": p.status,
                "ready": p.ready,
                "restarts": p.restarts,
                "node": p.node,
                "age": p.age,
                "ip": p.ip,
            }
            for p in pods
        ]
