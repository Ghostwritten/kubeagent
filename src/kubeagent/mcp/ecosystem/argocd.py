"""ArgoCD ecosystem plugin — tools for GitOps application management."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.base import BaseTool


def _run_argocd(*args: str, timeout: int = 30) -> dict[str, Any]:
    """Run an argocd CLI command."""
    cmd = ["argocd", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # Try JSON parsing first
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        if result.returncode != 0:
            return {"error": output, "command": " ".join(cmd)}
        try:
            return json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return {"output": output}
    except FileNotFoundError:
        return {
            "error": "argocd CLI not found. Install: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
        }
    except subprocess.TimeoutExpired:
        return {"error": f"argocd command timed out ({timeout}s)"}


class ArgoCDAppListTool(BaseTool):
    name = "argocd_app_list"
    description = "List all ArgoCD applications."
    security_level = SecurityLevel.SAFE

    def execute(self, project: str = "", **kwargs: Any) -> Any:
        args = ["app", "list", "-o", "json"]
        if project:
            args.extend(["-p", project])
        return _run_argocd(*args)


class ArgoCDAppGetTool(BaseTool):
    name = "argocd_app_get"
    description = "Get detailed information about an ArgoCD application."
    security_level = SecurityLevel.SAFE

    def execute(self, app_name: str = "", **kwargs: Any) -> Any:
        if not app_name:
            return {"error": "app_name is required"}
        return _run_argocd("app", "get", app_name, "-o", "json")


class ArgoCDAppSyncTool(BaseTool):
    name = "argocd_app_sync"
    description = "Sync an ArgoCD application to its target state."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        app_name: str = "",
        dry_run: bool = False,
        prune: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not app_name:
            return {"error": "app_name is required"}
        args = ["app", "sync", app_name]
        if dry_run:
            args.append("--dry-run")
        if prune:
            args.append("--prune")
        return _run_argocd(*args)


class ArgoCDAppStatusTool(BaseTool):
    name = "argocd_app_status"
    description = "Show sync and health status of an ArgoCD application."
    security_level = SecurityLevel.SAFE

    def execute(self, app_name: str = "", **kwargs: Any) -> Any:
        if not app_name:
            return {"error": "app_name is required"}
        result = _run_argocd("app", "get", app_name, "-o", "json")
        if "error" in result:
            return result
        # Extract just the status fields
        if isinstance(result, dict) and "status" in result:
            status = result["status"]
            return {
                "app": app_name,
                "sync_status": status.get("sync", {}).get("status", "Unknown"),
                "health_status": status.get("health", {}).get("status", "Unknown"),
                "revision": status.get("sync", {}).get("revision", ""),
            }
        return result


class ArgoCDAppHistoryTool(BaseTool):
    name = "argocd_app_history"
    description = "Show deployment history of an ArgoCD application."
    security_level = SecurityLevel.SAFE

    def execute(self, app_name: str = "", **kwargs: Any) -> Any:
        if not app_name:
            return {"error": "app_name is required"}
        return _run_argocd("app", "history", app_name)


class ArgoCDAppRollbackTool(BaseTool):
    name = "argocd_app_rollback"
    description = "Rollback an ArgoCD application to a previous revision."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        app_name: str = "",
        revision: int = 0,
        **kwargs: Any,
    ) -> Any:
        if not app_name:
            return {"error": "app_name is required"}
        if revision <= 0:
            return {"error": "revision must be a positive integer"}
        return _run_argocd("app", "rollback", app_name, str(revision))


ARGOCD_TOOLS: list[type[BaseTool]] = [
    ArgoCDAppListTool,
    ArgoCDAppGetTool,
    ArgoCDAppSyncTool,
    ArgoCDAppStatusTool,
    ArgoCDAppHistoryTool,
    ArgoCDAppRollbackTool,
]
