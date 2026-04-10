"""Core agent module for KubeAgent."""

from __future__ import annotations

from dataclasses import dataclass

from kubeagent.config.settings import KubeAgentConfig


@dataclass
class KubeAgentDeps:
    """Dependency injection container for the KubeAgent."""

    config: KubeAgentConfig
