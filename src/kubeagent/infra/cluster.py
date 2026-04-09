"""Kubernetes cluster context management."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ClusterInfo:
    """Information about a Kubernetes cluster."""

    name: str
    server: str
    ca_data: str | None = None
    insecure_skip_tls: bool = False
    auth_provider: str | None = None
    token: str | None = None
    cert_data: str | None = None
    key_data: str | None = None


@dataclass
class ClusterContext:
    """Represents a named context in kubeconfig."""

    name: str
    cluster: str
    user: str
    namespace: str = "default"
    is_current: bool = False


class KubeconfigManager:
    """Manages kubeconfig loading, parsing, and context switching."""

    def __init__(self, kubeconfig_path: str | None = None) -> None:
        if kubeconfig_path:
            self.kubeconfig_path = Path(kubeconfig_path).expanduser()
        else:
            self.kubeconfig_path = self._resolve_kubeconfig_path()
        self._config: dict[str, Any] = {}
        self._load()

    def _resolve_kubeconfig_path(self) -> Path:
        """Resolve kubeconfig path from KUBECONFIG env or default."""
        kubeconfig_env = os.environ.get("KUBECONFIG")
        if kubeconfig_env:
            first_path = kubeconfig_env.split(":")[0]
            resolved = Path(first_path).expanduser()
            if resolved.exists():
                return resolved

        default = Path.home() / ".kube" / "config"
        if default.exists():
            return default

        return default

    def _load(self) -> None:
        """Load and parse kubeconfig."""
        if not self.kubeconfig_path.exists():
            self._config = {"contexts": [], "clusters": [], "users": []}
            return

        with open(self.kubeconfig_path) as f:
            self._config = yaml.safe_load(f) or {}

    def reload(self) -> None:
        """Reload kubeconfig from disk."""
        self._load()

    @property
    def raw(self) -> dict[str, Any]:
        """Raw kubeconfig data."""
        return self._config

    def get_clusters(self) -> dict[str, ClusterInfo]:
        """Get all clusters from kubeconfig."""
        clusters: dict[str, ClusterInfo] = {}
        for c in self._config.get("clusters", []):
            cd = c.get("cluster", {})
            clusters[c["name"]] = ClusterInfo(
                name=c["name"],
                server=cd.get("server", ""),
                ca_data=cd.get("certificate-authority-data"),
                insecure_skip_tls=cd.get("insecure-skip-tls-verify", False),
            )
        return clusters

    def get_users(self) -> dict[str, dict[str, Any]]:
        """Get all users from kubeconfig."""
        return {u["name"]: u.get("user", {}) for u in self._config.get("users", [])}

    def get_contexts(self) -> list[ClusterContext]:
        """Get all contexts from kubeconfig."""
        current = self._config.get("current-context", "")
        contexts: list[ClusterContext] = []
        for ctx in self._config.get("contexts", []):
            ctx_data = ctx.get("context", {})
            contexts.append(
                ClusterContext(
                    name=ctx["name"],
                    cluster=ctx_data.get("cluster", ""),
                    user=ctx_data.get("user", ""),
                    namespace=ctx_data.get("namespace", "default"),
                    is_current=ctx["name"] == current,
                )
            )
        return contexts

    def get_current_context(self) -> ClusterContext | None:
        """Get the current context."""
        current_name = self._config.get("current-context", "")
        for ctx in self.get_contexts():
            if ctx.name == current_name:
                return ctx
        return None

    def get_cluster_info(self, cluster_name: str) -> ClusterInfo | None:
        """Get cluster info by name."""
        return self.get_clusters().get(cluster_name)

    def context_exists(self, context_name: str) -> bool:
        """Check if a context exists."""
        return any(ctx.name == context_name for ctx in self.get_contexts())

    def switch_context(self, context_name: str) -> bool:
        """Switch to a different context by updating kubeconfig."""
        if not self.context_exists(context_name):
            return False

        self._config["current-context"] = context_name
        self.kubeconfig_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.kubeconfig_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        return True

    def get_cluster_server(self, context_name: str) -> str | None:
        """Get the API server URL for a context."""
        ctx = next((c for c in self.get_contexts() if c.name == context_name), None)
        if not ctx:
            return None
        info = self.get_cluster_info(ctx.cluster)
        return info.server if info else None

    def get_user_for_context(self, context_name: str) -> dict[str, Any]:
        """Get user credentials for a context."""
        ctx = next((c for c in self.get_contexts() if c.name == context_name), None)
        if not ctx:
            return {}
        return self.get_users().get(ctx.user, {})


STATE_FILE = Path.home() / ".kubeagent" / "state.json"


def load_state() -> dict[str, Any]:
    """Load persistent state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict[str, Any]) -> None:
    """Save persistent state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
