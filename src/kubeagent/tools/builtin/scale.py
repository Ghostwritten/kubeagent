"""Tool: scale resource."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class ScaleResourceTool(BaseTool):
    name = "scale_resource"
    description = "Scale a deployment or statefulset to a given replica count."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        executor: PythonClientExecutor,
        kind: str,
        name: str,
        namespace: str = "default",
        replicas: int = 1,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return executor.scale_resource(
            kind=kind, name=name, namespace=namespace, replicas=replicas, dry_run=dry_run
        )
