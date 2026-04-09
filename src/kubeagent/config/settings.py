"""Configuration models for KubeAgent."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """LLM model configuration."""

    default: str = "claude-sonnet-4-20250514"
    fallback: list[str] = Field(default_factory=lambda: ["gpt-4o", "ollama/qwen2.5"])
    strategy: str = "complexity"  # complexity | cost | availability | manual
    subagent_model: str = "claude-haiku-4-5-20251001"
    api_key: str | None = None
    api_base: str | None = None


class ClusterConfig(BaseModel):
    """Kubernetes cluster configuration."""

    kubeconfig: str = str(Path.home() / ".kube" / "config")
    default_namespace: str = "default"


class OutputConfig(BaseModel):
    """Output formatting configuration."""

    style: str = "mixed"  # rich | markdown | mixed
    language: str = "auto"  # auto | en | zh
    verbose: bool = False


class KubeAgentConfig(BaseModel):
    """Root configuration for KubeAgent."""

    model: ModelConfig = Field(default_factory=ModelConfig)
    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    initialized: bool = False


CONFIG_DIR = Path.home() / ".kubeagent"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def load_config() -> KubeAgentConfig:
    """Load configuration from disk, or return defaults if not found."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
        return KubeAgentConfig(**data)
    return KubeAgentConfig()


def save_config(config: KubeAgentConfig) -> None:
    """Save configuration to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.initialized = True
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)


def config_exists() -> bool:
    """Check if configuration file exists and is initialized."""
    if not CONFIG_FILE.exists():
        return False
    config = load_config()
    return config.initialized


def get_env_api_key() -> str | None:
    """Check environment variables for API keys."""
    for var in ["KUBEAGENT_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
        key = os.environ.get(var)
        if key:
            return key
    return None


def detect_kubeconfig() -> str | None:
    """Detect kubeconfig path."""
    # Check KUBECONFIG env var first
    kubeconfig_env = os.environ.get("KUBECONFIG")
    if kubeconfig_env:
        # KUBECONFIG can have multiple paths separated by :
        first_path = kubeconfig_env.split(":")[0]
        if Path(first_path).exists():
            return first_path

    # Check default path
    default_path = Path.home() / ".kube" / "config"
    if default_path.exists():
        return str(default_path)

    return None
