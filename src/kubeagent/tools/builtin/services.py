"""Tool: get services."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetServicesTool(BaseTool):
    name = "get_services"
    description = "List services in a namespace with type, cluster IP, and ports."
    security_level = SecurityLevel.SAFE

    def execute(self, executor: PythonClientExecutor, namespace: str = "default") -> list[dict]:
        services = executor.list_services(namespace=namespace)
        return [
            {
                "name": s.name,
                "namespace": s.namespace,
                "type": s.type,
                "cluster_ip": s.cluster_ip,
                "external_ip": s.external_ip,
                "ports": ",".join(s.ports),
                "age": s.age,
            }
            for s in services
        ]
