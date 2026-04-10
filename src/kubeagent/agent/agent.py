"""KubeAgent — Pydantic AI agent with Kubernetes tools."""

from __future__ import annotations

import inspect
import json
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from kubeagent.agent.deps import KubeAgentDeps
from kubeagent.agent.model import get_agent_model
from kubeagent.agent.policy import PolicyDecision, build_impact_description, check_policy
from kubeagent.agent.prompts import SYSTEM_PROMPT
from kubeagent.config.settings import KubeAgentConfig, load_config
from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.registry import get_registry

# ---------------------------------------------------------------------------
# Input models for each tool (used for pydantic-ai tool schema generation)
# ---------------------------------------------------------------------------


class GetPodsInput(BaseModel):
    """Input for get_pods."""

    namespace: str = Field(default="", description="Namespace to query. Empty = all namespaces.")
    label_selector: dict[str, str] | None = Field(default=None, description="Filter by labels.")


class GetNodesInput(BaseModel):
    """Input for get_nodes."""


class GetNamespacesInput(BaseModel):
    """Input for get_namespaces."""


class GetServicesInput(BaseModel):
    """Input for get_services."""

    namespace: str = Field(default="default", description="Namespace to query.")


class GetConfigMapsInput(BaseModel):
    """Input for get_configmaps."""

    namespace: str = Field(default="default", description="Namespace to query.")


class DescribeResourceInput(BaseModel):
    """Input for describe_resource."""

    kind: str = Field(description="Resource kind: pod, node, service, configmap, deployment, etc.")
    name: str = Field(description="Resource name.")
    namespace: str = Field(default="default", description="Namespace.")


class GetEventsInput(BaseModel):
    """Input for get_events."""

    namespace: str = Field(default="", description="Namespace. Empty = all namespaces.")
    field_selector: str = Field(default="", description="Kubernetes field selector filter.")


class GetPodLogsInput(BaseModel):
    """Input for get_pod_logs."""

    name: str = Field(description="Pod name.")
    namespace: str = Field(default="default", description="Namespace.")
    container: str | None = Field(default=None, description="Container name.")
    tail_lines: int = Field(default=100, description="Number of log lines to fetch.")


class ApplyYamlInput(BaseModel):
    """Input for apply_yaml."""

    yaml_content: str = Field(description="YAML content for the resource(s) to apply.")
    namespace: str = Field(default="default", description="Target namespace.")
    dry_run: bool = Field(default=False, description="Preview changes without applying.")


class DeleteResourceInput(BaseModel):
    """Input for delete_resource."""

    kind: str = Field(description="Resource kind.")
    name: str = Field(description="Resource name.")
    namespace: str = Field(default="default", description="Namespace.")
    dry_run: bool = Field(default=False, description="Preview deletion.")


class ScaleResourceInput(BaseModel):
    """Input for scale_resource."""

    kind: str = Field(description="Kind (deployment or statefulset).")
    name: str = Field(description="Resource name.")
    namespace: str = Field(default="default", description="Namespace.")
    replicas: int = Field(description="Target replica count.")
    dry_run: bool = Field(default=False, description="Preview scaling.")


class RestartPodInput(BaseModel):
    """Input for restart_pod."""

    name: str = Field(description="Pod name.")
    namespace: str = Field(default="default", description="Namespace.")


class CordonNodeInput(BaseModel):
    """Input for cordon_node."""

    name: str = Field(description="Node name.")


class UncordonNodeInput(BaseModel):
    """Input for uncordon_node."""

    name: str = Field(description="Node name.")


class DrainNodeInput(BaseModel):
    """Input for drain_node."""

    name: str = Field(description="Node name.")
    force: bool = Field(default=False, description="Force delete non-daemonset pods.")


class KubectlExecInput(BaseModel):
    """Input for kubectl_exec."""

    pod: str = Field(description="Pod name.")
    namespace: str = Field(default="default", description="Namespace.")
    container: str | None = Field(default=None, description="Container name.")
    command: list[str] = Field(
        default_factory=lambda: ["/bin/sh"],
        description="Command to execute as a list of strings.",
    )


class KubectlTopInput(BaseModel):
    """Input for kubectl_top."""

    resource: str = Field(default="pods", description="Resource type: pods or nodes.")
    namespace: str = Field(default="", description="Namespace filter.")
    selector: str = Field(default="", description="Label selector filter.")


class KubectlApplyFileInput(BaseModel):
    """Input for kubectl_apply_file."""

    file_path: str = Field(description="Path to the YAML manifest file.")
    namespace: str = Field(default="default", description="Target namespace.")


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------


def create_agent(
    config: KubeAgentConfig | None = None,
    system_prompt: str | None = None,
) -> Agent[KubeAgentDeps, str]:
    """Create and configure the KubeAgent with all tools bound."""
    if config is None:
        config = load_config()

    model = get_agent_model(config.model)
    prompt = system_prompt or SYSTEM_PROMPT

    agent: Agent[KubeAgentDeps, str] = Agent(
        model=model,
        system_prompt=prompt,
        deps_type=KubeAgentDeps,
        output_type=str,
        retries=2,
        defer_model_check=True,
    )

    _register_read_tools(agent)
    _register_write_tools(agent)
    _register_kubectl_tools(agent)

    return agent


# ---------------------------------------------------------------------------
# Tool registration helpers
# ---------------------------------------------------------------------------


def _get_executor(ctx: RunContext[KubeAgentDeps]) -> PythonClientExecutor:
    """Create an executor from the current context."""
    return PythonClientExecutor(kubeconfig_path=ctx.deps.config.cluster.kubeconfig)


def _format_result(result: Any) -> str:
    """Format a tool result for LLM consumption."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        if not result:
            return "No results found."
        lines: list[str] = []
        for i, item in enumerate(result):
            if isinstance(item, dict):
                parts = [f"{k}={v}" for k, v in item.items() if v is not None]
                lines.append(f"  {i + 1}. {' | '.join(parts)}")
            else:
                lines.append(f"  {i + 1}. {item}")
        return "\n".join(lines)
    if isinstance(result, dict):
        lines = []
        for k, v in result.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                lines.append(f"{k}:")
                for item in v:
                    parts = [f"{ik}={iv}" for ik, iv in item.items() if iv is not None]
                    lines.append(f"  - {' | '.join(parts)}")
            elif isinstance(v, list):
                lines.append(f"{k}: {', '.join(str(x) for x in v)}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)
    return str(result)


def _call_tool(tool_class: type, ctx: RunContext[KubeAgentDeps], **kwargs: Any) -> str:
    """Execute a tool with policy check and format the result."""

    tool = tool_class()
    deps = ctx.deps

    # --- Policy gate ---
    if tool.security_level != SecurityLevel.SAFE:
        registry = get_registry()
        decision = check_policy(
            tool.name,
            registry,
            args=kwargs,
            auto_approve=deps.auto_approve,
            dry_run=deps.dry_run,
        )
        if decision == PolicyDecision.DENY:
            return f"DENIED: Tool '{tool.name}' is not permitted."
        if decision == PolicyDecision.CONFIRM:
            impact = build_impact_description(tool.name, kwargs or {}, registry)
            return (
                f"CONFIRMATION REQUIRED: {impact} "
                "The user must confirm this operation before it can proceed. "
                "Ask the user to confirm, or suggest they use /yes to enable auto-approve mode."
            )

    # --- Dry-run override ---
    if deps.dry_run and "dry_run" in inspect.signature(tool.execute).parameters:
        kwargs["dry_run"] = True

    try:
        executor = _get_executor(ctx)
        result = tool.execute(executor, **kwargs)
        formatted = _format_result(result)

        # --- Audit logging (non-SAFE operations only) ---
        if tool.security_level != SecurityLevel.SAFE and deps.memory is not None:
            deps.memory.audit.log(
                cluster=None,
                namespace=kwargs.get("namespace"),
                tool_name=tool.name,
                args=kwargs,
                result=formatted[:200],
                success=True,
            )

        if deps.dry_run:
            return f"[DRY-RUN] {formatted}"
        return formatted
    except ConnectionError as e:
        _audit_failure(tool, deps, kwargs, f"Cannot connect to cluster — {e}")
        return f"Error: Cannot connect to cluster — {e}"
    except RuntimeError as e:
        _audit_failure(tool, deps, kwargs, str(e))
        return f"Error: {e}"
    except Exception as e:
        _audit_failure(tool, deps, kwargs, str(e))
        return f"Unexpected error: {e}"


def _audit_failure(tool: Any, deps: Any, kwargs: dict, error: str) -> None:
    """Log a failed tool execution to audit."""
    if tool.security_level != SecurityLevel.SAFE and deps.memory is not None:
        deps.memory.audit.log(
            cluster=None,
            namespace=kwargs.get("namespace"),
            tool_name=tool.name,
            args=kwargs,
            result=error[:200],
            success=False,
        )


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------


def _register_read_tools(agent: Agent[KubeAgentDeps, str]) -> None:
    """Register all read-only tools."""
    from kubeagent.tools.builtin.configmaps import GetConfigMapsTool
    from kubeagent.tools.builtin.describe import DescribeResourceTool
    from kubeagent.tools.builtin.events import GetEventsTool
    from kubeagent.tools.builtin.logs import GetPodLogsTool
    from kubeagent.tools.builtin.namespaces import GetNamespacesTool
    from kubeagent.tools.builtin.nodes import GetNodesTool
    from kubeagent.tools.builtin.pods import GetPodsTool
    from kubeagent.tools.builtin.services import GetServicesTool

    @agent.tool(retries=1)
    async def get_pods(ctx: RunContext[KubeAgentDeps], input_data: GetPodsInput) -> str:
        """List pods with status, ready count, restarts, node, and age."""
        labels = input_data.label_selector
        if labels and isinstance(labels, str):
            # Tool input may come as JSON string
            labels = json.loads(labels)
        return _call_tool(GetPodsTool, ctx, namespace=input_data.namespace, label_selector=labels)

    @agent.tool(retries=1)
    async def get_nodes(ctx: RunContext[KubeAgentDeps]) -> str:
        """List all nodes with status, roles, version, and allocatable resources."""
        return _call_tool(GetNodesTool, ctx)

    @agent.tool(retries=1)
    async def get_namespaces(ctx: RunContext[KubeAgentDeps]) -> str:
        """List all namespaces in the cluster."""
        return _call_tool(GetNamespacesTool, ctx)

    @agent.tool(retries=1)
    async def get_services(ctx: RunContext[KubeAgentDeps], input_data: GetServicesInput) -> str:
        """List services in a namespace with type, cluster IP, and ports."""
        return _call_tool(GetServicesTool, ctx, namespace=input_data.namespace)

    @agent.tool(retries=1)
    async def get_configmaps(ctx: RunContext[KubeAgentDeps], input_data: GetConfigMapsInput) -> str:
        """List configmaps in a namespace."""
        return _call_tool(GetConfigMapsTool, ctx, namespace=input_data.namespace)

    @agent.tool(retries=1)
    async def describe_resource(
        ctx: RunContext[KubeAgentDeps], input_data: DescribeResourceInput
    ) -> str:
        """Get full details of a Kubernetes resource by kind and name."""
        return _call_tool(
            DescribeResourceTool,
            ctx,
            kind=input_data.kind,
            name=input_data.name,
            namespace=input_data.namespace,
        )

    @agent.tool(retries=1)
    async def get_events(ctx: RunContext[KubeAgentDeps], input_data: GetEventsInput) -> str:
        """Get recent events in a namespace or across the cluster."""
        return _call_tool(
            GetEventsTool,
            ctx,
            namespace=input_data.namespace,
            field_selector=input_data.field_selector,
        )

    @agent.tool(retries=1)
    async def get_pod_logs(ctx: RunContext[KubeAgentDeps], input_data: GetPodLogsInput) -> str:
        """Fetch logs from a pod container."""
        return _call_tool(
            GetPodLogsTool,
            ctx,
            name=input_data.name,
            namespace=input_data.namespace,
            container=input_data.container,
            tail_lines=input_data.tail_lines,
        )


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------


def _register_write_tools(agent: Agent[KubeAgentDeps, str]) -> None:
    """Register all write operation tools."""
    from kubeagent.tools.builtin.apply import ApplyYamlTool
    from kubeagent.tools.builtin.delete import DeleteResourceTool
    from kubeagent.tools.builtin.nodes_ops import CordonNodeTool, DrainNodeTool, UncordonNodeTool
    from kubeagent.tools.builtin.restart import RestartPodTool
    from kubeagent.tools.builtin.scale import ScaleResourceTool

    @agent.tool(retries=0)
    async def apply_yaml(ctx: RunContext[KubeAgentDeps], input_data: ApplyYamlInput) -> str:
        """Create or update resources from YAML. SENSITIVE: modifies cluster state."""
        return _call_tool(
            ApplyYamlTool,
            ctx,
            yaml_content=input_data.yaml_content,
            namespace=input_data.namespace,
            dry_run=input_data.dry_run,
        )

    @agent.tool(retries=0)
    async def delete_resource(
        ctx: RunContext[KubeAgentDeps], input_data: DeleteResourceInput
    ) -> str:
        """Delete a resource by kind and name. DANGEROUS: irreversibly removes resources."""
        return _call_tool(
            DeleteResourceTool,
            ctx,
            kind=input_data.kind,
            name=input_data.name,
            namespace=input_data.namespace,
            dry_run=input_data.dry_run,
        )

    @agent.tool(retries=0)
    async def scale_resource(ctx: RunContext[KubeAgentDeps], input_data: ScaleResourceInput) -> str:
        """Scale a deployment or statefulset. SENSITIVE: changes replica count."""
        return _call_tool(
            ScaleResourceTool,
            ctx,
            kind=input_data.kind,
            name=input_data.name,
            namespace=input_data.namespace,
            replicas=input_data.replicas,
            dry_run=input_data.dry_run,
        )

    @agent.tool(retries=0)
    async def restart_pod(ctx: RunContext[KubeAgentDeps], input_data: RestartPodInput) -> str:
        """Restart a pod by deleting it. DANGEROUS: causes pod disruption."""
        return _call_tool(RestartPodTool, ctx, name=input_data.name, namespace=input_data.namespace)

    @agent.tool(retries=0)
    async def cordon_node(ctx: RunContext[KubeAgentDeps], input_data: CordonNodeInput) -> str:
        """Mark a node as unschedulable. DANGEROUS: stops new pods from being scheduled."""
        return _call_tool(CordonNodeTool, ctx, name=input_data.name)

    @agent.tool(retries=1)
    async def uncordon_node(ctx: RunContext[KubeAgentDeps], input_data: UncordonNodeInput) -> str:
        """Mark a node as schedulable again."""
        return _call_tool(UncordonNodeTool, ctx, name=input_data.name)

    @agent.tool(retries=0)
    async def drain_node(ctx: RunContext[KubeAgentDeps], input_data: DrainNodeInput) -> str:
        """Drain a node: cordon + evict all non-daemonset pods. DANGEROUS: disrupts workloads."""
        return _call_tool(DrainNodeTool, ctx, name=input_data.name, force=input_data.force)


# ---------------------------------------------------------------------------
# kubectl tools
# ---------------------------------------------------------------------------


def _register_kubectl_tools(agent: Agent[KubeAgentDeps, str]) -> None:
    """Register kubectl wrapper tools."""
    from kubeagent.tools.builtin.kubectl import (
        KubectlApplyFileTool,
        KubectlExecTool,
        KubectlTopTool,
    )

    @agent.tool(retries=1)
    async def kubectl_exec(ctx: RunContext[KubeAgentDeps], input_data: KubectlExecInput) -> str:
        """Execute a command in a pod via kubectl exec."""
        return _call_tool(
            KubectlExecTool,
            ctx,
            pod=input_data.pod,
            namespace=input_data.namespace,
            container=input_data.container,
            command=input_data.command,
        )

    @agent.tool(retries=1)
    async def kubectl_top(ctx: RunContext[KubeAgentDeps], input_data: KubectlTopInput) -> str:
        """Show resource (CPU/memory) usage for pods or nodes."""
        return _call_tool(
            KubectlTopTool,
            ctx,
            resource=input_data.resource,
            namespace=input_data.namespace,
            selector=input_data.selector,
        )

    @agent.tool(retries=0)
    async def kubectl_apply_file(
        ctx: RunContext[KubeAgentDeps], input_data: KubectlApplyFileInput
    ) -> str:
        """Apply a YAML manifest file via kubectl apply -f. SENSITIVE: modifies cluster state."""
        return _call_tool(
            KubectlApplyFileTool,
            ctx,
            file_path=input_data.file_path,
            namespace=input_data.namespace,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_single_turn(
    prompt: str,
    config: KubeAgentConfig | None = None,
) -> str:
    """Run a single-turn conversation.

    Args:
        prompt: User's natural language query.
        config: Optional config override.

    Returns:
        Agent's text response.
    """
    if config is None:
        config = load_config()

    agent = create_agent(config)
    deps = KubeAgentDeps(config=config)

    result = await agent.run(prompt, deps=deps)
    return result.output


async def run_single_turn_stream(
    prompt: str,
    config: KubeAgentConfig | None = None,
):
    """Run a single-turn conversation with streaming.

    Yields text chunks as they arrive.
    """
    if config is None:
        config = load_config()

    agent = create_agent(config)
    deps = KubeAgentDeps(config=config)

    async with agent.run_stream(prompt, deps=deps) as response:
        async for chunk in response.stream_text(delta=True):
            yield chunk
