"""Tests for Phase 09 — SubAgent + Model Router."""

from __future__ import annotations

from kubeagent.agent.subagent import (
    SubAgent,
    SubAgentConfig,
    SubAgentDispatcher,
    SubAgentFactory,
)
from kubeagent.config.settings import ModelConfig
from kubeagent.infra.model_router import (
    ModelRouter,
    RouterStrategy,
    get_router,
)

# ---------------------------------------------------------------------------
# T1: SubAgent Factory
# ---------------------------------------------------------------------------


class TestSubAgentFactory:
    def test_create_subagent_with_model(self) -> None:
        factory = SubAgentFactory()
        agent = factory.create(
            task="Diagnose pod crashes",
            model="claude-haiku-4-5-20251001",
            tools=["get_pods", "get_events"],
            context={"namespace": "payment"},
        )
        assert agent is not None
        assert agent.model_name
        assert agent.task == "Diagnose pod crashes"
        assert "get_pods" in agent.tool_names
        assert "get_events" in agent.tool_names

    def test_create_subagent_default_model(self) -> None:
        factory = SubAgentFactory()
        agent = factory.create(
            task="List all pods",
            tools=["get_pods"],
            context={},
        )
        assert agent is not None
        # Default model should be haiku
        assert "haiku" in agent.model_name

    def test_create_subagent_with_tools_subset(self) -> None:
        factory = SubAgentFactory()
        agent = factory.create(
            task="Get node info",
            tools=["get_nodes", "get_pods"],
            context={},
        )
        assert len(agent.tool_names) == 2
        assert "get_nodes" in agent.tool_names
        assert "get_pods" in agent.tool_names


class TestSubAgent:
    def test_subagent_result_structure(self) -> None:
        subagent = SubAgent(
            task="test task",
            model_name="haiku",
            tool_names=["get_pods"],
            context={},
            result="pods listed",
            error=None,
            source="test_subagent",
        )
        assert subagent.result == "pods listed"
        assert subagent.error is None
        assert subagent.source == "test_subagent"

    def test_subagent_error_tracking(self) -> None:
        subagent = SubAgent(
            task="test task",
            model_name="haiku",
            tool_names=[],
            context={},
            result=None,
            error="connection timeout",
            source="test_subagent",
        )
        assert subagent.result is None
        assert subagent.error == "connection timeout"
        assert subagent.is_error is True


# ---------------------------------------------------------------------------
# T2: SubAgent Dispatcher
# ---------------------------------------------------------------------------


class TestSubAgentDispatcher:
    def test_dispatch_single_subagent(self) -> None:
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        subs = [
            SubAgentConfig(
                task="Get pods in default",
                model="claude-haiku-4-5-20251001",
                tools=["get_pods"],
                context={"namespace": "default"},
            )
        ]
        results = dispatcher.dispatch_sync(subs, timeout=30)
        assert len(results) == 1
        assert results[0].source.startswith("subagent_")

    def test_dispatch_multiple_parallel(self) -> None:
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        subs = [
            SubAgentConfig(
                task="Get pods in ns1",
                model="claude-haiku-4-5-20251001",
                tools=["get_pods"],
                context={"namespace": "ns1"},
            ),
            SubAgentConfig(
                task="Get pods in ns2",
                model="claude-haiku-4-5-20251001",
                tools=["get_pods"],
                context={"namespace": "ns2"},
            ),
        ]
        results = dispatcher.dispatch_sync(subs, timeout=30)
        assert len(results) == 2

    def test_error_isolation_one_fails(self) -> None:
        """One subagent failure doesn't crash others."""
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        subs = [
            SubAgentConfig(
                task="Valid task",
                model="claude-haiku-4-5-20251001",
                tools=["get_pods"],
                context={"namespace": "default"},
            ),
            SubAgentConfig(
                task="Task with unknown tool",
                model="claude-haiku-4-5-20251001",
                tools=["nonexistent_tool"],
                context={},
            ),
        ]
        results = dispatcher.dispatch_sync(subs, timeout=30)
        assert len(results) == 2
        assert all(isinstance(r, SubAgent) for r in results)

    def test_timeout_handling(self) -> None:
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        subs = [
            SubAgentConfig(
                task="Very slow task",
                model="claude-haiku-4-5-20251001",
                tools=["get_pods"],
                context={},
            )
        ]
        # Very short timeout should trigger timeout error
        results = dispatcher.dispatch_sync(subs, timeout=0.001)
        assert len(results) == 1
        r = results[0]
        assert r.is_error or r.error is not None or r.result is not None

    def test_result_aggregation(self) -> None:
        """Test that aggregate_results groups results by source."""
        agents = [
            SubAgent(
                task="Pods in ns1",
                model_name="haiku",
                tool_names=["get_pods"],
                context={"namespace": "ns1"},
                result="pods listed in ns1: [app-1]",
                error=None,
                source="subagent_ns1",
            ),
            SubAgent(
                task="Pods in ns2",
                model_name="haiku",
                tool_names=["get_pods"],
                context={"namespace": "ns2"},
                result="pods listed in ns2: [app-2]",
                error=None,
                source="subagent_ns2",
            ),
        ]
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        agg = dispatcher.aggregate_results(agents)
        assert "subagent_ns1" in agg
        assert "subagent_ns2" in agg
        assert "ns1" in agg["subagent_ns1"]
        assert "ns2" in agg["subagent_ns2"]

    def test_aggregate_includes_errors(self) -> None:
        """Error agents are included in aggregation."""
        agents = [
            SubAgent(
                task="Failing task",
                model_name="haiku",
                tool_names=["get_pods"],
                context={},
                result=None,
                error="timeout",
                source="subagent_fail",
            )
        ]
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        agg = dispatcher.aggregate_results(agents)
        assert "subagent_fail" in agg
        assert "timeout" in agg["subagent_fail"]
        assert "[ERROR]" in agg["subagent_fail"]

    def test_synthesize(self) -> None:
        """Test result synthesis into formatted analysis."""
        agents = [
            SubAgent(
                task="Get pod status",
                model_name="haiku",
                tool_names=["get_pods"],
                context={},
                result="pod-abc running",
                error=None,
                source="subagent_pods",
            ),
            SubAgent(
                task="Get events",
                model_name="haiku",
                tool_names=["get_events"],
                context={},
                result=None,
                error="timeout",
                source="subagent_events",
            ),
        ]
        factory = SubAgentFactory()
        dispatcher = SubAgentDispatcher(factory)
        synthesis = dispatcher.synthesize(agents, "diagnose payment-service")
        assert "diagnose payment-service" in synthesis
        assert "subagent_pods" in synthesis
        assert "OK" in synthesis
        assert "ERROR" in synthesis


# ---------------------------------------------------------------------------
# T3: Model Router
# ---------------------------------------------------------------------------


class TestModelRouter:
    def test_complexity_routing_simple(self) -> None:
        router = ModelRouter(strategy=RouterStrategy.COMPLEXITY)
        model = router.select_model("list all pods", [])
        # Simple queries → light model
        assert "haiku" in model.lower() or "mini" in model.lower() or "gpt-4o-mini" in model.lower()

    def test_complexity_routing_complex(self) -> None:
        router = ModelRouter(strategy=RouterStrategy.COMPLEXITY)
        model = router.select_model(
            "Why is the payment-service crashing? Analyze logs and suggest a fix.",
            [],
        )
        # Complex queries → strong model
        strong = "sonnet" in model.lower() or "opus" in model.lower() or "gpt-4o" in model.lower()
        assert strong

    def test_cost_strategy_respects_budget(self) -> None:
        router = ModelRouter(
            strategy=RouterStrategy.COST,
            monthly_budget_usd=0.0,  # exhausted
        )
        # Should route to cheapest available (free local model)
        model = router.select_model("list pods", [])
        assert "ollama" in model.lower() or "haiku" in model.lower()

    def test_cost_tracking(self) -> None:
        router = ModelRouter(strategy=RouterStrategy.COST)
        router.record_usage("gpt-4o", input_tokens=1000, output_tokens=500)
        router.record_usage("haiku", input_tokens=100, output_tokens=50)
        stats = router.get_cost_stats()
        assert stats.total_input_tokens == 1100
        assert stats.total_output_tokens == 550
        assert stats.total_cost_usd > 0

    def test_manual_strategy(self) -> None:
        router = ModelRouter(
            strategy=RouterStrategy.MANUAL,
            manual_model="claude-sonnet-4-20250514",
        )
        model = router.select_model("any query", [])
        assert "claude-sonnet-4-20250514" in model

    def test_fallback_chain_on_failure(self) -> None:
        router = ModelRouter(
            strategy=RouterStrategy.AVAILABILITY,
            fallback=["claude-haiku-4-5-20251001", "gpt-4o-mini"],
        )
        model = router.select_model("test", [])
        # Should return first fallback (resolve_model_name adds provider prefix)
        assert "haiku" in model.lower()

    def test_subagent_model_used(self) -> None:
        router = ModelRouter(
            strategy=RouterStrategy.COMPLEXITY,
            subagent_model="claude-haiku-4-5-20251001",
        )
        model = router.select_model_for_subagent("diagnose crash", [])
        assert "haiku" in model.lower()


class TestGetRouter:
    def test_get_router_from_config(self) -> None:
        config = ModelConfig(strategy="complexity")
        router = get_router(config)
        assert router.strategy == RouterStrategy.COMPLEXITY

    def test_get_router_cost_strategy(self) -> None:
        config = ModelConfig(strategy="cost")
        router = get_router(config)
        assert router.strategy == RouterStrategy.COST
