"""Tool: kubectl operations (exec, top, apply-file)."""

from __future__ import annotations

from typing import Any

from kubeagent.infra.executor import SecurityLevel
from kubeagent.infra.kubectl import (
    kubectl_apply_file,
    kubectl_exec,
    kubectl_top,
)
from kubeagent.tools.base import BaseTool


class KubectlExecTool(BaseTool):
    name = "kubectl_exec"
    description = "Execute a command in a pod via kubectl exec."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        pod: str,
        namespace: str = "default",
        container: str | None = None,
        command: list[str] | None = None,
        **_kwargs: object,
    ) -> dict[str, Any]:
        result = kubectl_exec(pod=pod, namespace=namespace, container=container, command=command)
        return {
            "ok": result.ok,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


class KubectlTopTool(BaseTool):
    name = "kubectl_top"
    description = "Show resource (CPU/memory) usage for pods or nodes."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        resource: str = "pods",
        namespace: str = "",
        selector: str = "",
        **_kwargs: object,
    ) -> dict[str, Any]:
        result = kubectl_top(resource=resource, namespace=namespace, selector=selector)
        return {
            "ok": result.ok,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


class KubectlApplyFileTool(BaseTool):
    name = "kubectl_apply_file"
    description = "Apply a YAML manifest file via kubectl apply -f."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        file_path: str,
        namespace: str = "default",
        **_kwargs: object,
    ) -> dict[str, Any]:
        result = kubectl_apply_file(file_path=file_path, namespace=namespace)
        return {
            "ok": result.ok,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
