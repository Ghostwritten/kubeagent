"""Tool: get pod logs."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetPodLogsTool(BaseTool):
    name = "get_pod_logs"
    description = "Fetch logs from a pod container. Returns log lines."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        executor: PythonClientExecutor,
        name: str,
        namespace: str = "default",
        container: str | None = None,
        tail_lines: int = 100,
    ) -> dict:
        log_entry = executor.get_pod_logs(
            name=name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
        )
        return {
            "pod": log_entry.pod_name,
            "container": log_entry.container,
            "lines": log_entry.lines,
            "line_count": len(log_entry.lines),
        }
