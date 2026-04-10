"""Model abstraction — resolves model names and creates pydantic-ai agents."""

from __future__ import annotations

from dataclasses import dataclass

from kubeagent.config.settings import ModelConfig


@dataclass
class ModelInfo:
    """Resolved model information for pydantic-ai."""

    model_name: str  # e.g. "openai:gpt-4o", "anthropic:claude-sonnet-4-20250514"
    provider: str  # e.g. "openai", "anthropic", "ollama"
    is_local: bool


# Provider prefix mapping for pydantic-ai
_PROVIDER_MAP: dict[str, str] = {
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "claude": "anthropic",
    "gemini": "google-gla",
    "llama": "ollama",
    "qwen": "ollama",
    "mistral": "mistral",
    "deepseek": "openai",  # deepseek uses OpenAI-compatible API
}

# Models that run locally via Ollama
_LOCAL_PROVIDERS = {"ollama"}


def resolve_model_name(model_id: str) -> str:
    """Convert a short model name to pydantic-ai format: 'provider:model'.

    Examples:
        'gpt-4o'         → 'openai:gpt-4o'
        'claude-sonnet-4-20250514' → 'anthropic:claude-sonnet-4-20250514'
        'ollama/llama3'  → 'ollama:llama3'
        'openai:gpt-4o'  → 'openai:gpt-4o'  (already prefixed)
    """
    # Already has provider prefix
    if ":" in model_id:
        return model_id

    # Ollama explicit format: ollama/model
    if model_id.startswith("ollama/"):
        return f"ollama:{model_id.removeprefix('ollama/')}"

    # Match by prefix
    for prefix, provider in _PROVIDER_MAP.items():
        if model_id.startswith(prefix):
            return f"{provider}:{model_id}"

    # Fallback: treat as OpenAI-compatible
    return f"openai:{model_id}"


def get_model_info(model_id: str) -> ModelInfo:
    """Get resolved model info from a model identifier."""
    full_name = resolve_model_name(model_id)
    provider = full_name.split(":")[0]
    return ModelInfo(
        model_name=full_name,
        provider=provider,
        is_local=provider in _LOCAL_PROVIDERS,
    )


def get_agent_model(config: ModelConfig) -> str:
    """Get the pydantic-ai model string from config.

    Returns the primary model in pydantic-ai format.
    """
    return resolve_model_name(config.default)


def get_fallback_models(config: ModelConfig) -> list[str]:
    """Get fallback model strings in pydantic-ai format."""
    return [resolve_model_name(m) for m in config.fallback]
