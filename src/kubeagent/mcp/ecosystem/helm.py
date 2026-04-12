"""Helm ecosystem plugin — tools and skills for Helm chart management."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.base import BaseTool


def _run_helm(*args: str, timeout: int = 30) -> dict[str, Any]:
    """Run a helm CLI command and return parsed output."""
    cmd = ["helm", *args, "-o", "json"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip(), "command": " ".join(cmd)}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout.strip()}
    except FileNotFoundError:
        return {"error": "helm CLI not found. Install: https://helm.sh/docs/intro/install/"}
    except subprocess.TimeoutExpired:
        return {"error": f"helm command timed out ({timeout}s)"}


def _run_helm_text(*args: str, timeout: int = 60) -> dict[str, Any]:
    """Run a helm command that doesn't support JSON output."""
    cmd = ["helm", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip(), "command": " ".join(cmd)}
        return {"output": result.stdout.strip()}
    except FileNotFoundError:
        return {"error": "helm CLI not found. Install: https://helm.sh/docs/intro/install/"}
    except subprocess.TimeoutExpired:
        return {"error": f"helm command timed out ({timeout}s)"}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class HelmListTool(BaseTool):
    name = "helm_list"
    description = "List all installed Helm releases across namespaces."
    security_level = SecurityLevel.SAFE

    def execute(self, namespace: str = "", all_namespaces: bool = True, **kwargs: Any) -> Any:
        args = ["list"]
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args.extend(["-n", namespace])
        return _run_helm(*args)


class HelmInstallTool(BaseTool):
    name = "helm_install"
    description = "Install a Helm chart as a new release."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        release_name: str = "",
        chart: str = "",
        namespace: str = "default",
        values: dict[str, Any] | None = None,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not release_name or not chart:
            return {"error": "release_name and chart are required"}
        args = ["install", release_name, chart, "-n", namespace]
        if dry_run:
            args.append("--dry-run")
        if values:
            for k, v in values.items():
                args.extend(["--set", f"{k}={v}"])
        return _run_helm_text(*args)


class HelmUpgradeTool(BaseTool):
    name = "helm_upgrade"
    description = "Upgrade an existing Helm release to a new chart version."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        release_name: str = "",
        chart: str = "",
        namespace: str = "default",
        values: dict[str, Any] | None = None,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not release_name or not chart:
            return {"error": "release_name and chart are required"}
        args = ["upgrade", release_name, chart, "-n", namespace]
        if dry_run:
            args.append("--dry-run")
        if values:
            for k, v in values.items():
                args.extend(["--set", f"{k}={v}"])
        return _run_helm_text(*args)


class HelmRollbackTool(BaseTool):
    name = "helm_rollback"
    description = "Rollback a Helm release to a previous revision."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        release_name: str = "",
        revision: int = 0,
        namespace: str = "default",
        **kwargs: Any,
    ) -> Any:
        if not release_name:
            return {"error": "release_name is required"}
        args = ["rollback", release_name, "-n", namespace]
        if revision > 0:
            args.append(str(revision))
        return _run_helm_text(*args)


class HelmUninstallTool(BaseTool):
    name = "helm_uninstall"
    description = "Uninstall a Helm release."
    security_level = SecurityLevel.DANGEROUS

    def execute(
        self,
        release_name: str = "",
        namespace: str = "default",
        dry_run: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not release_name:
            return {"error": "release_name is required"}
        args = ["uninstall", release_name, "-n", namespace]
        if dry_run:
            args.append("--dry-run")
        return _run_helm_text(*args)


class HelmStatusTool(BaseTool):
    name = "helm_status"
    description = "Show the status of a Helm release."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        release_name: str = "",
        namespace: str = "default",
        **kwargs: Any,
    ) -> Any:
        if not release_name:
            return {"error": "release_name is required"}
        return _run_helm("status", release_name, "-n", namespace)


class HelmHistoryTool(BaseTool):
    name = "helm_history"
    description = "Show release history (revisions) for a Helm release."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        release_name: str = "",
        namespace: str = "default",
        **kwargs: Any,
    ) -> Any:
        if not release_name:
            return {"error": "release_name is required"}
        return _run_helm("history", release_name, "-n", namespace)


# ---------------------------------------------------------------------------
# Convenience: all tools
# ---------------------------------------------------------------------------

HELM_TOOLS: list[type[BaseTool]] = [
    HelmListTool,
    HelmInstallTool,
    HelmUpgradeTool,
    HelmRollbackTool,
    HelmUninstallTool,
    HelmStatusTool,
    HelmHistoryTool,
]
