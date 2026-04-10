"""Model Router — intelligent model selection strategies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from kubeagent.agent.model import resolve_model_name
from kubeagent.config.settings import ModelConfig

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Routing Strategies
# ---------------------------------------------------------------------------


class RouterStrategy(Enum):
    """Model routing strategy."""

    COMPLEXITY = "complexity"  # Route by query complexity
    COST = "cost"  # Route by cost, respect budget
    AVAILABILITY = "availability"  # Fallback chain on failure
    MANUAL = "manual"  # User-specified model


# ---------------------------------------------------------------------------
# Complexity Classification
# ---------------------------------------------------------------------------


class ComplexityLevel(Enum):
    """Query complexity level."""

    SIMPLE = "simple"  # Single-resource read (list, get)
    MODERATE = "moderate"  # Multi-resource, cross-namespace
    COMPLEX = "complex"  # Diagnosis, planning, multi-step analysis


# Keywords that indicate complex queries
_COMPLEX_PATTERNS = [
    r"why\s+[^\?]+\?(?!\s*$)",  # "why is X crashing?"
    r"debug",
    r"diagnos",
    r"analyz",
    r"root\s*cause",
    r"investigate",
    r"recommend",
    r"suggest\s+(a\s+)?fix",
    r"fix\s+the",
    r"troubleshoot",
    r"compare\s+",
    r"optimi[sz]",
    r"plan\s+",
    r"strategy",
    r"memory\s+leak",
    r"cpu\s+spike",
    r"latency",
    r"performance\s+issue",
    r"deployment\s+fail",
    r"crashloop",
    r"pending\s+pod",
    r"evicted",
    r"oomkill",
    r"imagepullbackoff",
]

# Keywords that indicate simple queries
_SIMPLE_PATTERNS = [
    r"^list\s+",
    r"^get\s+",
    r"^show\s+",
    r"^what\s+is\s+(the\s+)?",
    r"^how\s+many\s+",
    r"count",
    r"total",
    r"summary",
    r"status",
    r"namespaces",
    r"pods\s*$",
    r"nodes\s*$",
    r"events\s*$",
]


def classify_complexity(query: str) -> ComplexityLevel:
    """Classify a query's complexity based on keywords."""
    query_lower = query.lower()

    for pattern in _COMPLEX_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return ComplexityLevel.COMPLEX

    for pattern in _SIMPLE_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return ComplexityLevel.SIMPLE

    return ComplexityLevel.MODERATE


# ---------------------------------------------------------------------------
# Cost Tracking
# ---------------------------------------------------------------------------

# Estimated cost per 1M tokens (input + output combined)
# Based on 2025 pricing
_MODEL_COST_PER_1M: dict[str, float] = {
    # Anthropic
    "haiku": 0.25,
    "sonnet": 3.0,
    "opus": 15.0,
    # OpenAI
    "gpt-4o": 5.0,
    "gpt-4o-mini": 0.3,
    "gpt-4-turbo": 10.0,
    "o1": 15.0,
    "o1-mini": 0.3,
    # Google
    "gemini-1.5": 1.25,
    "gemini-2.0": 0.0,  # unknown
    # Ollama (free)
    "ollama": 0.0,
}


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a model call."""
    model_lower = model_name.lower()

    # Find matching cost entry
    rate = 0.0
    for key, val in _MODEL_COST_PER_1M.items():
        if key in model_lower:
            rate = val
            break

    total_tokens = input_tokens + output_tokens
    return (total_tokens / 1_000_000) * rate


@dataclass
class CostStats:
    """Accumulated cost statistics."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    calls_by_model: dict[str, int] = field(default_factory=dict)

    def add(self, model_name: str, input_tokens: int, output_tokens: int) -> None:
        cost = estimate_cost(model_name, input_tokens, output_tokens)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost
        self.calls_by_model[model_name] = self.calls_by_model.get(model_name, 0) + 1


# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------


@dataclass
class ModelRouter:
    """Intelligent model selection based on configured strategy.

    Strategies:
    - COMPLEXITY: Route by query complexity (simple → light, complex → strong)
    - COST: Track usage, respect monthly budget, prefer cheap models
    - AVAILABILITY: Use fallback chain when primary model fails
    - MANUAL: Always use user-specified model
    """

    strategy: RouterStrategy
    fallback: list[str] = field(default_factory=list)
    manual_model: str | None = None
    subagent_model: str | None = None
    monthly_budget_usd: float | None = None
    _cost_stats: CostStats = field(default_factory=CostStats, init=False)
    _heavy_models: tuple[str, ...] = field(
        default_factory=lambda: (
            "claude-opus",
            "gpt-4o",
            "sonnet",
            "opus",
        )
    )
    _light_models: tuple[str, ...] = field(
        default_factory=lambda: (
            "haiku",
            "gpt-4o-mini",
            "o1-mini",
            "mini",
        )
    )

    def select_model(
        self,
        query: str,
        tool_names: list[str],
    ) -> str:
        """Select the appropriate model for a query."""
        if self.strategy == RouterStrategy.MANUAL:
            return resolve_model_name(self.manual_model or "claude-haiku-4-5-20251001")

        if self.strategy == RouterStrategy.AVAILABILITY:
            return resolve_model_name(
                self.fallback[0] if self.fallback else "claude-haiku-4-5-20251001"
            )

        if self.strategy == RouterStrategy.COST:
            return self._select_cost_effective(query, tool_names)

        if self.strategy == RouterStrategy.COMPLEXITY:
            return self._select_by_complexity(query, tool_names)

        # Fallback
        return resolve_model_name("claude-haiku-4-5-20251001")

    def select_model_for_subagent(
        self,
        task: str,
        tool_names: list[str],
    ) -> str:
        """Select model for a SubAgent. Uses subagent_model if configured."""
        if self.subagent_model:
            return resolve_model_name(self.subagent_model)
        return self.select_model(task, tool_names)

    def _select_by_complexity(
        self,
        query: str,
        tool_names: list[str],
    ) -> str:
        """Route based on query complexity."""
        complexity = classify_complexity(query)

        if complexity == ComplexityLevel.SIMPLE:
            # Simple queries → light model
            return resolve_model_name("claude-haiku-4-5-20251001")
        elif complexity == ComplexityLevel.COMPLEX:
            # Complex queries → strong model
            return resolve_model_name("claude-sonnet-4-20250514")
        else:
            # Moderate → mid-tier
            return resolve_model_name("claude-haiku-4-5-20251001")

    def _select_cost_effective(
        self,
        query: str,
        tool_names: list[str],
    ) -> str:
        """Select cheapest model that fits the task."""
        budget_exhausted = (
            self.monthly_budget_usd is not None
            and self._cost_stats.total_cost_usd >= self.monthly_budget_usd
        )
        if budget_exhausted:
            # Budget exhausted — use free/cheapest
            return resolve_model_name("ollama/qwen2.5")

        complexity = classify_complexity(query)
        if complexity == ComplexityLevel.COMPLEX:
            # Complex still needs strong model
            return resolve_model_name("claude-sonnet-4-20250514")
        return resolve_model_name("claude-haiku-4-5-20251001")

    def record_usage(
        self,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record a model usage event for cost tracking."""
        self._cost_stats.add(model_name, input_tokens, output_tokens)

    def get_cost_stats(self) -> CostStats:
        """Return accumulated cost statistics."""
        return self._cost_stats

    def reset_cost_stats(self) -> None:
        """Reset accumulated cost statistics."""
        self._cost_stats = CostStats()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


_DEFAULT_ROUTER: ModelRouter | None = None
_DEFAULT_CONFIG: ModelConfig | None = None


def get_router(config: ModelConfig | None = None) -> ModelRouter:
    """Get or create a ModelRouter singleton for the given config."""
    global _DEFAULT_ROUTER, _DEFAULT_CONFIG

    cfg = config or ModelConfig()
    if _DEFAULT_ROUTER is None or _DEFAULT_CONFIG is not cfg:
        strategy = RouterStrategy(cfg.strategy)
        _DEFAULT_ROUTER = ModelRouter(
            strategy=strategy,
            fallback=[resolve_model_name(m) for m in cfg.fallback],
            subagent_model=resolve_model_name(cfg.subagent_model) if cfg.subagent_model else None,
        )
        _DEFAULT_CONFIG = cfg

    return _DEFAULT_ROUTER
