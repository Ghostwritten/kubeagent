"""Tool: restart pod."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class RestartPodTool(BaseTool):
    name = "restart_pod"
    description = "Restart a pod by deleting it (deployment will recreate)."
    security_level = SecurityLevel.DANGEROUS

    def execute(
        self,
        executor: PythonClientExecutor,
        name: str,
        namespace: str = "default",
    ) -> dict[str, Any]:
        return executor.restart_pod(name=name, namespace=namespace)
