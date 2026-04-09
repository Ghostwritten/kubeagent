"""Tests for tool base, registry, and builtin tools."""

from __future__ import annotations

from unittest.mock import MagicMock

from kubeagent.infra.executor import (
    EventInfo,
    K8sResource,
    LogEntry,
    NodeInfo,
    PodInfo,
    SecurityLevel,
    ServiceInfo,
)
from kubeagent.tools.base import BaseTool
from kubeagent.tools.registry import ToolRegistry, get_registry


class TestBaseTool:
    def test_default_values(self) -> None:
        tool = BaseTool()
        assert tool.name == ""
        assert tool.description == ""
        assert tool.security_level == SecurityLevel.SAFE

    def test_to_dict(self) -> None:
        tool = BaseTool()
        d = tool.to_dict()
        assert d == {
            "name": "",
            "description": "",
            "security_level": "safe",
        }

    def test_execute_raises(self) -> None:
        tool = BaseTool()
        import pytest

        with pytest.raises(NotImplementedError):
            tool.execute()


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        registry = ToolRegistry()

        class MyTool(BaseTool):
            name = "my_tool"
            description = "test"
            security_level = SecurityLevel.SAFE

        registry.register(MyTool)
        assert registry.get("my_tool") is MyTool

    def test_get_missing_returns_none(self) -> None:
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_register_no_name_raises(self) -> None:
        registry = ToolRegistry()

        class NoNameTool(BaseTool):
            pass

        import pytest

        with pytest.raises(ValueError, match="has no name"):
            registry.register(NoNameTool)

    def test_list_tools(self) -> None:
        registry = ToolRegistry()

        class Tool1(BaseTool):
            name = "tool_1"
            description = "first"
            security_level = SecurityLevel.SAFE

        class Tool2(BaseTool):
            name = "tool_2"
            description = "second"
            security_level = SecurityLevel.SENSITIVE

        registry.register(Tool1)
        registry.register(Tool2)

        tools = registry.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"tool_1", "tool_2"}

    def test_filter_by_security(self) -> None:
        registry = ToolRegistry()

        class SafeTool(BaseTool):
            name = "safe_tool"
            description = "safe"
            security_level = SecurityLevel.SAFE

        class SensitiveTool(BaseTool):
            name = "sensitive_tool"
            description = "sensitive"
            security_level = SecurityLevel.SENSITIVE

        registry.register(SafeTool)
        registry.register(SensitiveTool)

        safe = registry.filter_by_security(SecurityLevel.SAFE)
        assert len(safe) == 1
        assert safe[0]().name == "safe_tool"

    def test_len(self) -> None:
        registry = ToolRegistry()
        assert len(registry) == 0

        class T(BaseTool):
            name = "t"
            description = "t"

        registry.register(T)
        assert len(registry) == 1


class TestGetRegistry:
    def test_discovers_builtin_tools(self) -> None:
        registry = get_registry()
        # Should have at least 8 builtin tools
        assert len(registry) >= 8
        assert registry.get("get_pods") is not None
        assert registry.get("get_nodes") is not None
        assert registry.get("get_namespaces") is not None
        assert registry.get("get_services") is not None
        assert registry.get("get_configmaps") is not None
        assert registry.get("describe_resource") is not None
        assert registry.get("get_events") is not None
        assert registry.get("get_pod_logs") is not None


def _mock_pod(name: str = "nginx-123", namespace: str = "default", **kwargs) -> PodInfo:
    return PodInfo(
        name=name,
        namespace=namespace,
        status=kwargs.get("status", "Running"),
        age=kwargs.get("age", "5m"),
        ready=kwargs.get("ready", "1/1"),
        restarts=kwargs.get("restarts", 0),
        node=kwargs.get("node", "node-1"),
        ip=kwargs.get("ip", "10.0.0.1"),
    )


def _mock_node(name: str = "node-1", **kwargs) -> NodeInfo:
    return NodeInfo(
        name=name,
        roles=kwargs.get("roles", ["master"]),
        status_text=kwargs.get("status_text", "Ready"),
        version=kwargs.get("version", "v1.28.0"),
        age=kwargs.get("age", "30d"),
        cpu_allocatable=kwargs.get("cpu_allocatable", "4"),
        memory_allocatable=kwargs.get("memory_allocatable", "8Gi"),
    )


def _mock_service(name: str = "svc-1", **kwargs) -> ServiceInfo:
    return ServiceInfo(
        name=name,
        namespace=kwargs.get("namespace", "default"),
        type=kwargs.get("type", "ClusterIP"),
        cluster_ip=kwargs.get("cluster_ip", "10.96.0.1"),
        external_ip=kwargs.get("external_ip", "<none>"),
        ports=kwargs.get("ports", ["80/TCP"]),
        age=kwargs.get("age", "10d"),
    )


def _mock_executor():
    return MagicMock()


class TestGetPodsTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.pods import GetPodsTool

        executor = _mock_executor()
        executor.list_pods.return_value = [_mock_pod(), _mock_pod(name="nginx-456")]

        tool = GetPodsTool()
        result = tool.execute(executor)
        assert len(result) == 2
        assert result[0]["name"] == "nginx-123"
        assert result[1]["name"] == "nginx-456"
        assert result[0]["status"] == "Running"


class TestGetNodesTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.nodes import GetNodesTool

        executor = _mock_executor()
        executor.list_nodes.return_value = [_mock_node()]

        tool = GetNodesTool()
        result = tool.execute(executor)
        assert len(result) == 1
        assert result[0]["name"] == "node-1"
        assert result[0]["roles"] == "master"
        assert result[0]["version"] == "v1.28.0"


class TestGetNamespacesTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.namespaces import GetNamespacesTool

        executor = _mock_executor()
        executor.list_namespaces.return_value = [
            K8sResource(kind="Namespace", name="default", status="Active", age="30d"),
            K8sResource(kind="Namespace", name="kube-system", status="Active", age="30d"),
        ]

        tool = GetNamespacesTool()
        result = tool.execute(executor)
        assert len(result) == 2
        assert result[0]["name"] == "default"
        assert result[1]["name"] == "kube-system"


class TestGetServicesTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.services import GetServicesTool

        executor = _mock_executor()
        executor.list_services.return_value = [_mock_service()]

        tool = GetServicesTool()
        result = tool.execute(executor)
        assert len(result) == 1
        assert result[0]["name"] == "svc-1"
        assert result[0]["type"] == "ClusterIP"
        assert result[0]["ports"] == "80/TCP"


class TestGetConfigMapsTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.configmaps import GetConfigMapsTool

        executor = _mock_executor()
        executor.list_configmaps.return_value = [
            K8sResource(kind="ConfigMap", name="cm-1", namespace="default", age="5d"),
        ]

        tool = GetConfigMapsTool()
        result = tool.execute(executor)
        assert len(result) == 1
        assert result[0]["name"] == "cm-1"
        assert result[0]["namespace"] == "default"


class TestDescribeResourceTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.describe import DescribeResourceTool

        executor = _mock_executor()
        executor.describe_resource.return_value = {"kind": "Pod", "metadata": {"name": "nginx"}}

        tool = DescribeResourceTool()
        result = tool.execute(executor, kind="pod", name="nginx")
        assert result["kind"] == "Pod"
        executor.describe_resource.assert_called_once_with(
            kind="pod", name="nginx", namespace="default"
        )

    def test_execute_not_found(self) -> None:
        from kubeagent.tools.builtin.describe import DescribeResourceTool

        executor = _mock_executor()
        executor.describe_resource.return_value = None

        tool = DescribeResourceTool()
        result = tool.execute(executor, kind="pod", name="missing")
        assert result is None


class TestGetEventsTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.events import GetEventsTool

        executor = _mock_executor()
        executor.get_events.return_value = [
            EventInfo(
                type="Normal",
                reason="Started",
                message="Started container nginx",
                source="kubelet",
                count=1,
                age="5m",
                involved_object="Pod/nginx-123",
            ),
        ]

        tool = GetEventsTool()
        result = tool.execute(executor)
        assert len(result) == 1
        assert result[0]["type"] == "Normal"
        assert result[0]["reason"] == "Started"
        assert result[0]["source"] == "kubelet"


class TestGetPodLogsTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.logs import GetPodLogsTool

        executor = _mock_executor()
        executor.get_pod_logs.return_value = LogEntry(
            pod_name="nginx-123",
            container="nginx",
            lines=["line 1", "line 2", "line 3"],
        )

        tool = GetPodLogsTool()
        result = tool.execute(executor, name="nginx-123")
        assert result["pod"] == "nginx-123"
        assert result["container"] == "nginx"
        assert result["line_count"] == 3
        executor.get_pod_logs.assert_called_once_with(
            name="nginx-123",
            namespace="default",
            container=None,
            tail_lines=100,
        )
