"""MCP server — exposes KubeAgent tools and skills via Model Context Protocol."""

from __future__ import annotations

import inspect
import json
from typing import Any

from fastmcp import FastMCP

from kubeagent.infra.executor import PythonClientExecutor
from kubeagent.skills.registry import SkillRegistry
from kubeagent.tools.base import BaseTool
from kubeagent.tools.registry import get_registry


class KubeAgentMCPServer:
    """MCP server that exposes all KubeAgent tools and skills.

    Tools become MCP tools (callable by clients).
    Skills become MCP resources (readable context for clients).
    """

    def __init__(
        self,
        name: str = "kubeagent",
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self._name = name
        self._host = host
        self._port = port
        self._mcp = FastMCP(name)
        self._executor: PythonClientExecutor | None = None
        self._skill_registry: SkillRegistry | None = None
        self._setup()

    def _get_executor(self) -> PythonClientExecutor:
        """Lazy-initialize the K8s executor."""
        if self._executor is None:
            self._executor = PythonClientExecutor()
        return self._executor

    def _get_skill_registry(self) -> SkillRegistry:
        """Lazy-initialize the skill registry."""
        if self._skill_registry is None:
            self._skill_registry = SkillRegistry()
        return self._skill_registry

    def _setup(self) -> None:
        """Register all tools and skills with the MCP server."""
        self._register_tools()
        self._register_ecosystem_tools()
        self._register_skills()

    def _register_tools(self) -> None:
        """Register all KubeAgent tools as MCP tools."""
        registry = get_registry()
        for tool_info in registry.list_tools():
            tool_name = tool_info["name"]
            tool_class = registry.get(tool_name)
            if tool_class is None:
                continue
            self._register_single_tool(tool_name, tool_info, tool_class)

    def _register_ecosystem_tools(self) -> None:
        """Register ecosystem tools (Helm, Istio, ArgoCD, Prometheus, Grafana)."""
        from kubeagent.mcp.ecosystem.argocd import ARGOCD_TOOLS
        from kubeagent.mcp.ecosystem.grafana import GRAFANA_TOOLS
        from kubeagent.mcp.ecosystem.helm import HELM_TOOLS
        from kubeagent.mcp.ecosystem.istio import ISTIO_TOOLS
        from kubeagent.mcp.ecosystem.prometheus import PROMETHEUS_TOOLS

        all_ecosystem = HELM_TOOLS + ISTIO_TOOLS + ARGOCD_TOOLS + PROMETHEUS_TOOLS + GRAFANA_TOOLS
        for tool_class in all_ecosystem:
            instance = tool_class()
            info = instance.to_dict()
            self._register_single_tool(instance.name, info, tool_class)
        self._ecosystem_count = len(all_ecosystem)

    def _register_single_tool(
        self,
        tool_name: str,
        tool_info: dict[str, str],
        tool_class: type[BaseTool],
    ) -> None:
        """Register a single tool as an MCP tool.

        Each tool is exposed with a single `params_json` argument
        (JSON string of key-value pairs), because FastMCP requires
        explicit signatures and our tools have heterogeneous parameters.
        """
        description = tool_info.get("description", "")
        security_level = tool_info.get("security_level", "safe")

        # Collect parameter docs from the execute() signature
        instance_for_sig = tool_class() if isinstance(tool_class, type) else tool_class()
        sig = inspect.signature(instance_for_sig.execute)
        param_names = [
            name
            for name, p in sig.parameters.items()
            if name not in ("self", "executor")
            and p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)
        ]
        params_doc = f"Accepted params: {', '.join(param_names)}" if param_names else ""

        server_ref = self

        async def handler(params_json: str = "{}") -> str:
            """Execute the tool with JSON parameters."""
            try:
                kwargs = json.loads(params_json) if params_json else {}
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in params_json"})

            instance = tool_class() if isinstance(tool_class, type) else tool_class()
            exec_sig = inspect.signature(instance.execute)
            if "executor" in exec_sig.parameters:
                kwargs["executor"] = server_ref._get_executor()
            try:
                result = instance.execute(**kwargs)
                return json.dumps(result, default=str, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)})

        full_desc = f"{description} [security: {security_level}]"
        if params_doc:
            full_desc = f"{full_desc}. {params_doc}"

        handler.__name__ = tool_name
        handler.__doc__ = full_desc

        self._mcp.tool(name=tool_name, description=full_desc)(handler)

    def _register_skills(self) -> None:
        """Register all skills as MCP resources."""
        skill_reg = self._get_skill_registry()
        for skill_name in skill_reg.list_skills():
            skill = skill_reg.get(skill_name)
            if skill is None:
                continue
            self._register_single_skill(skill_name, skill)

    def _register_single_skill(self, skill_name: str, skill: Any) -> None:
        """Register a single skill as a static MCP resource."""
        from fastmcp.resources import TextResource

        resource_uri = f"skill://{skill_name}"
        description = getattr(skill, "description", "")

        skill_data = {
            "name": skill_name,
            "description": description,
            "trigger": getattr(skill, "trigger", ""),
            "steps": getattr(skill, "steps", []),
            "required_tools": getattr(skill, "required_tools", []),
        }

        content = json.dumps(skill_data, ensure_ascii=False)

        resource = TextResource(
            uri=resource_uri,
            name=skill_name,
            description=description,
            text=content,
            mime_type="application/json",
        )
        self._mcp.add_resource(resource)

    def get_mcp(self) -> FastMCP:
        """Return the underlying FastMCP instance."""
        return self._mcp

    def run(self, transport: str = "stdio") -> None:
        """Start the MCP server.

        Args:
            transport: "stdio" for stdin/stdout, "sse" for HTTP SSE.
        """
        if transport == "sse":
            self._mcp.run(transport="sse", host=self._host, port=self._port)
        else:
            self._mcp.run(transport="stdio")

    @property
    def tool_count(self) -> int:
        """Number of registered MCP tools (core + ecosystem)."""
        return len(get_registry().list_tools()) + getattr(self, "_ecosystem_count", 0)

    @property
    def skill_count(self) -> int:
        """Number of registered MCP resources (skills)."""
        return len(self._get_skill_registry().list_skills())
