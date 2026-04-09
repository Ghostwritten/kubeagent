"""Tool: describe resource."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class DescribeResourceTool(BaseTool):
    name = "describe_resource"
    description = "Get full details of a K8s resource by kind and name."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        executor: PythonClientExecutor,
        kind: str,
        name: str,
        namespace: str = "default",
    ) -> dict[str, Any] | None:
        return executor.describe_resource(kind=kind, name=name, namespace=namespace)
