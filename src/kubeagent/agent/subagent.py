"""SubAgent — ephemeral agent factory and dispatcher."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext

from kubeagent.agent.deps import KubeAgentDeps
from kubeagent.agent.model import resolve_model_name
from kubeagent.config.settings import KubeAgentConfig, ModelConfig

# ---------------------------------------------------------------------------
# SubAgent data classes
# ---------------------------------------------------------------------------


@dataclass
class SubAgent:
    """Result from a SubAgent execution."""

    task: str
    model_name: str
    tool_names: list[str]
    context: dict
    result: str | None
    error: str | None
    source: str  # unique identifier for this subagent
    is_error: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_error = self.error is not None


@dataclass
class SubAgentConfig:
    """Configuration for a SubAgent to be dispatched."""

    task: str
    tools: list[str]  # tool names to expose to this subagent
    model: str | None = None  # None = use default subagent model
    context: dict | None = None


# ---------------------------------------------------------------------------
# SubAgent Factory
# ---------------------------------------------------------------------------


class SubAgentFactory:
    """Creates ephemeral SubAgent instances at runtime.

    Each SubAgent is a Pydantic AI Agent instance scoped to a specific task
    with a limited tool set.
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        self._config = config or ModelConfig()
        self._default_model = resolve_model_name(
            self._config.subagent_model or "claude-haiku-4-5-20251001"
        )

    def create(
        self,
        task: str,
        tools: list[str],
        model: str | None = None,
        context: dict | None = None,
    ) -> SubAgent:
        """Create a SubAgent descriptor.

        Does NOT create the actual pydantic-ai agent yet — that happens at
        execution time in the dispatcher. This returns a lightweight descriptor
        that can be inspected and queued.
        """
        model_name = resolve_model_name(model) if model else self._default_model
        return SubAgent(
            task=task,
            model_name=model_name,
            tool_names=list(tools),
            context=context or {},
            result=None,
            error=None,
            source=f"subagent_{uuid.uuid4().hex[:8]}",
        )


# ---------------------------------------------------------------------------
# SubAgent Dispatcher
# ---------------------------------------------------------------------------


class SubAgentDispatcher:
    """Dispatches SubAgents and aggregates their results.

    Handles:
    - Parallel execution via asyncio.gather
    - Per-agent timeout
    - Error isolation (one failure doesn't crash others)
    - Result aggregation with source attribution
    """

    def __init__(self, factory: SubAgentFactory | None = None) -> None:
        self._factory = factory or SubAgentFactory()

    def dispatch_sync(
        self,
        configs: list[SubAgentConfig],
        timeout: float = 30.0,
    ) -> list[SubAgent]:
        """Synchronous wrapper around async dispatch.

        Use this from synchronous code (e.g., REPL). For async code use
        dispatch() directly.
        """
        return asyncio.run(self.dispatch(configs, timeout=timeout))

    async def dispatch(
        self,
        configs: list[SubAgentConfig],
        timeout: float = 30.0,
    ) -> list[SubAgent]:
        """Dispatch multiple SubAgents in parallel and wait for all results."""
        tasks = [self._run_subagent(cfg, timeout) for cfg in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error SubAgents
        out: list[SubAgent] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                cfg = configs[i]
                agent = self._factory.create(
                    task=cfg.task,
                    tools=cfg.tools,
                    model=cfg.model,
                    context=cfg.context,
                )
                agent.result = None
                agent.error = f"[dispatcher exception] {type(result).__name__}: {result}"
                out.append(agent)
            else:
                out.append(result)
        return out

    async def _run_subagent(
        self,
        config: SubAgentConfig,
        timeout: float,
    ) -> SubAgent:
        """Run a single SubAgent with timeout."""
        agent = self._factory.create(
            task=config.task,
            tools=config.tools,
            model=config.model,
            context=config.context,
        )

        try:
            result = await asyncio.wait_for(
                self._execute_agent(agent, config),
                timeout=timeout,
            )
            agent.result = result
            agent.error = None
        except TimeoutError:
            agent.result = None
            agent.error = f"[timeout] SubAgent exceeded {timeout}s limit"
        except Exception as e:
            agent.result = None
            agent.error = f"[error] {type(e).__name__}: {e}"

        return agent

    async def _execute_agent(self, agent: SubAgent, config: SubAgentConfig) -> str:
        """Execute a SubAgent and return its result.

        Creates a scoped pydantic-ai agent with the given tool set and task,
        runs it, and returns the output.
        """
        from pydantic_ai import Agent

        model = agent.model_name
        system_prompt = (
            f"You are a specialized sub-agent. Your task:\n{agent.task}\n\n"
            "Answer the task concisely using the available tools."
        )

        sub_agent: Agent[KubeAgentDeps, str] = Agent(
            model=model,
            system_prompt=system_prompt,
            deps_type=KubeAgentDeps,
            output_type=str,
            retries=1,
            defer_model_check=True,
        )

        # Register requested tools only
        await self._register_tools(sub_agent, agent.tool_names, config)

        deps = KubeAgentDeps(
            config=KubeAgentConfig(
                cluster=KubeAgentConfig().cluster,
            ),
            memory=None,  # SubAgents don't need memory by default
        )

        ctx = config.context or {}
        namespace = ctx.get("namespace", "default")

        # Build a minimal prompt based on task and context
        prompt = agent.task
        if namespace:
            prompt += f" (namespace: {namespace})"

        result = await sub_agent.run(prompt, deps=deps)
        return result.output

    async def _register_tools(
        self,
        agent: Agent[KubeAgentDeps, str],
        tool_names: list[str],
        config: SubAgentConfig,
    ) -> None:
        """Register requested tools onto a sub-agent."""

        # Import all tool classes to check name
        tool_registry: dict[str, type] = {}

        try:
            from kubeagent.tools.builtin.pods import GetPodsTool

            tool_registry["get_pods"] = GetPodsTool
        except ImportError:
            pass
        try:
            from kubeagent.tools.builtin.nodes import GetNodesTool

            tool_registry["get_nodes"] = GetNodesTool
        except ImportError:
            pass
        try:
            from kubeagent.tools.builtin.namespaces import GetNamespacesTool

            tool_registry["get_namespaces"] = GetNamespacesTool
        except ImportError:
            pass
        try:
            from kubeagent.tools.builtin.events import GetEventsTool

            tool_registry["get_events"] = GetEventsTool
        except ImportError:
            pass
        try:
            from kubeagent.tools.builtin.services import GetServicesTool

            tool_registry["get_services"] = GetServicesTool
        except ImportError:
            pass
        try:
            from kubeagent.tools.builtin.describe import DescribeResourceTool

            tool_registry["describe_resource"] = DescribeResourceTool
        except ImportError:
            pass
        try:
            from kubeagent.tools.builtin.logs import GetPodLogsTool

            tool_registry["get_pod_logs"] = GetPodLogsTool
        except ImportError:
            pass

        for name in tool_names:
            tool_cls = tool_registry.get(name)
            if tool_cls is None:
                continue  # Skip unknown tools silently

            if name == "get_pods":

                @agent.tool(retries=1)
                async def get_pods_tool(ctx: RunContext[KubeAgentDeps], namespace: str = "") -> str:
                    from kubeagent.agent.agent import _call_tool

                    ns = namespace or ctx.deps.config.cluster.default_namespace
                    return _call_tool(GetPodsTool, ctx, namespace=ns)

                continue

            if name == "get_events":

                @agent.tool(retries=1)
                async def get_events_tool(
                    ctx: RunContext[KubeAgentDeps], namespace: str = ""
                ) -> str:
                    from kubeagent.agent.agent import _call_tool

                    return _call_tool(GetEventsTool, ctx, namespace=namespace or "")

                continue

            if name == "get_nodes":

                @agent.tool(retries=1)
                async def get_nodes_tool(ctx: RunContext[KubeAgentDeps]) -> str:
                    from kubeagent.agent.agent import _call_tool

                    return _call_tool(GetNodesTool, ctx)
                    return _call_tool(GetNodesTool, ctx)

                continue

            # Fallback: generic wrapper for any known tool
            @agent.tool(retries=1)
            async def generic_tool(ctx: RunContext[KubeAgentDeps], **kwargs: str) -> str:
                from kubeagent.agent.agent import _call_tool

                return _call_tool(tool_cls, ctx, **kwargs)

    def aggregate_results(self, agents: list[SubAgent]) -> dict[str, str]:
        """Aggregate results from multiple SubAgents into a unified dict.

        Returns:
            Dict mapping source name to result/error text.
        """
        agg: dict[str, str] = {}
        for agent in agents:
            if agent.error:
                agg[agent.source] = f"[ERROR] {agent.error}"
            elif agent.result:
                agg[agent.source] = agent.result
            else:
                agg[agent.source] = "[NO RESULT]"
        return agg

    def synthesize(
        self,
        agents: list[SubAgent],
        main_task: str,
    ) -> str:
        """Synthesize SubAgent results into a unified analysis.

        Returns a formatted string combining all results with source attribution.
        """
        if not agents:
            return "No sub-agent results to synthesize."

        sections = [f"## SubAgent Analysis for: {main_task}\n"]
        for agent in agents:
            status = "ERROR" if agent.is_error else "OK"
            sections.append(f"### [{status}] {agent.source} — {agent.task}")
            sections.append(f"Model: `{agent.model_name}`")
            if agent.is_error:
                sections.append(f"**Error:** {agent.error}")
            else:
                sections.append(agent.result or "[no result]")
            sections.append("")

        return "\n".join(sections)
