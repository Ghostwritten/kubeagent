"""Tool: apply yaml."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class ApplyYamlTool(BaseTool):
    name = "apply_yaml"
    description = "Create or update Kubernetes resources from YAML content."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        executor: PythonClientExecutor,
        yaml_content: str,
        namespace: str = "default",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return executor.apply_yaml(yaml_content=yaml_content, namespace=namespace, dry_run=dry_run)
