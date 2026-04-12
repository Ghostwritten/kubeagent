"""Istio ecosystem plugin — tools for service mesh management."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.base import BaseTool


def _run_istioctl(*args: str, timeout: int = 30) -> dict[str, Any]:
    """Run an istioctl CLI command."""
    cmd = ["istioctl", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        return {
            "success": result.returncode == 0,
            "output": output,
            "command": " ".join(cmd),
        }
    except FileNotFoundError:
        return {"error": "istioctl not found. Install: https://istio.io/latest/docs/setup/getting-started/"}
    except subprocess.TimeoutExpired:
        return {"error": f"istioctl command timed out ({timeout}s)"}


class IstioAnalyzeTool(BaseTool):
    name = "istio_analyze"
    description = "Analyze Istio configuration for potential issues in a namespace."
    security_level = SecurityLevel.SAFE

    def execute(self, namespace: str = "", all_namespaces: bool = False, **kwargs: Any) -> Any:
        args = ["analyze"]
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args.extend(["-n", namespace])
        return _run_istioctl(*args)


class IstioProxyStatusTool(BaseTool):
    name = "istio_proxy_status"
    description = "Show synchronization status of all Envoy sidecars."
    security_level = SecurityLevel.SAFE

    def execute(self, pod: str = "", **kwargs: Any) -> Any:
        args = ["proxy-status"]
        if pod:
            args.append(pod)
        return _run_istioctl(*args)


class IstioProxyConfigTool(BaseTool):
    name = "istio_proxy_config"
    description = "Retrieve Envoy proxy configuration for a pod (routes, clusters, listeners)."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        config_type: str = "all",
        pod: str = "",
        namespace: str = "default",
        **kwargs: Any,
    ) -> Any:
        if not pod:
            return {"error": "pod name is required"}
        args = ["proxy-config", config_type, f"{pod}.{namespace}"]
        return _run_istioctl(*args)


class IstioVersionTool(BaseTool):
    name = "istio_version"
    description = "Show Istio control plane and data plane versions."
    security_level = SecurityLevel.SAFE

    def execute(self, **kwargs: Any) -> Any:
        return _run_istioctl("version")


ISTIO_TOOLS: list[type[BaseTool]] = [
    IstioAnalyzeTool,
    IstioProxyStatusTool,
    IstioProxyConfigTool,
    IstioVersionTool,
]
