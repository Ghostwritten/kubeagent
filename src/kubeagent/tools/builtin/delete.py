"""Tool: delete resource."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class DeleteResourceTool(BaseTool):
    name = "delete_resource"
    description = "Delete a Kubernetes resource by kind and name."
    security_level = SecurityLevel.DANGEROUS

    def execute(
        self,
        executor: PythonClientExecutor,
        kind: str,
        name: str,
        namespace: str = "default",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return executor.delete_resource(kind=kind, name=name, namespace=namespace, dry_run=dry_run)
