"""K8s Executor — unified interface for Kubernetes API operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from kubernetes import client, config
from kubernetes.client import ApiClient


class SecurityLevel(StrEnum):
    """Operation security classification."""

    SAFE = "safe"
    SENSITIVE = "sensitive"
    DANGEROUS = "dangerous"


@dataclass
class K8sResource:
    """Normalized Kubernetes resource representation."""

    kind: str = ""
    name: str = ""
    namespace: str | None = None
    status: str | None = None
    age: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PodInfo(K8sResource):
    """Detailed pod information."""

    kind: str = "Pod"
    ready: str = "0/0"
    restarts: int = 0
    node: str | None = None
    ip: str | None = None
    containers: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class NodeInfo(K8sResource):
    """Detailed node information."""

    kind: str = "Node"
    roles: list[str] = field(default_factory=list)
    status_text: str = "Unknown"
    version: str = ""
    cpu_allocatable: str = ""
    memory_allocatable: str = ""
    cpu_capacity: str = ""
    memory_capacity: str = ""
    conditions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ServiceInfo(K8sResource):
    """Service information."""

    kind: str = "Service"
    type: str = ""
    cluster_ip: str = ""
    external_ip: str = ""
    ports: list[str] = field(default_factory=list)


@dataclass
class EventInfo:
    """Kubernetes event."""

    type: str
    reason: str
    message: str
    source: str
    count: int
    age: str
    involved_object: str


@dataclass
class LogEntry:
    """Log entry from a pod."""

    pod_name: str
    container: str | None
    lines: list[str]


def _calc_age(creation_timestamp: str | None) -> str:
    """Calculate age from creation timestamp."""
    if not creation_timestamp:
        return "unknown"
    try:
        created = datetime.fromisoformat(creation_timestamp.replace("Z", "+00:00"))
        delta = datetime.now(created.tzinfo) - created
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if days > 0:
            return f"{days}d{hours}h"
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    except Exception:
        return "unknown"


def _labels_match(labels: dict[str, str], selector: dict[str, str] | None) -> bool:
    """Check if labels match a selector."""
    if not selector:
        return True
    return all(labels.get(k) == v for k, v in selector.items())


class KubeExecutor(ABC):
    """Abstract interface for K8s operations."""

    @abstractmethod
    def list_pods(
        self, namespace: str = "", label_selector: dict[str, str] | None = None
    ) -> list[PodInfo]: ...

    @abstractmethod
    def get_pod(self, name: str, namespace: str = "default") -> PodInfo | None: ...

    @abstractmethod
    def list_nodes(self) -> list[NodeInfo]: ...

    @abstractmethod
    def list_namespaces(self) -> list[K8sResource]: ...

    @abstractmethod
    def list_services(self, namespace: str = "default") -> list[ServiceInfo]: ...

    @abstractmethod
    def list_configmaps(self, namespace: str = "default") -> list[K8sResource]: ...

    @abstractmethod
    def describe_resource(
        self, kind: str, name: str, namespace: str = "default"
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_events(self, namespace: str = "", field_selector: str = "") -> list[EventInfo]: ...

    @abstractmethod
    def get_pod_logs(
        self,
        name: str,
        namespace: str = "default",
        container: str | None = None,
        tail_lines: int = 100,
    ) -> LogEntry: ...


class PythonClientExecutor(KubeExecutor):
    """K8s executor using the official Python client."""

    def __init__(self, kubeconfig_path: str | None = None) -> None:
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                config.load_kube_config()
            self.api_client = ApiClient()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to K8s cluster: {e}") from e

    def list_pods(
        self, namespace: str = "", label_selector: dict[str, str] | None = None
    ) -> list[PodInfo]:
        """List pods in namespace (empty = all namespaces)."""
        label_str = ",".join(f"{k}={v}" for k, v in (label_selector or {}).items()) or None

        try:
            if namespace:
                resp = self.v1.list_namespaced_pod(namespace, label_selector=label_str)
            else:
                resp = self.v1.list_pod_for_all_namespaces(label_selector=label_str)
        except Exception as e:
            raise RuntimeError(f"Failed to list pods: {e}") from e

        pods: list[PodInfo] = []
        for item in resp.items:
            if not _labels_match(item.metadata.labels or {}, label_selector):
                continue

            containers = item.spec.containers or []
            container_statuses = item.status.container_statuses or []
            ready_count = sum(1 for cs in container_statuses if cs.ready)
            restarts = sum(cs.restart_count for cs in container_statuses)

            pods.append(
                PodInfo(
                    name=item.metadata.name,
                    namespace=item.metadata.namespace,
                    status=item.status.phase or "Unknown",
                    age=_calc_age(item.metadata.creation_timestamp),
                    labels=item.metadata.labels or {},
                    ready=f"{ready_count}/{len(containers)}",
                    restarts=restarts,
                    node=item.spec.node_name,
                    ip=item.status.pod_ip,
                    raw=item.to_dict() if hasattr(item, "to_dict") else {},
                )
            )
        return pods

    def get_pod(self, name: str, namespace: str = "default") -> PodInfo | None:
        """Get a single pod by name."""
        try:
            item = self.v1.read_namespaced_pod(name, namespace)
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise RuntimeError(f"Failed to get pod: {e}") from e

        containers = item.spec.containers or []
        container_statuses = item.status.container_statuses or []
        ready_count = sum(1 for cs in container_statuses if cs.ready)
        restarts = sum(cs.restart_count for cs in container_statuses)

        return PodInfo(
            name=item.metadata.name,
            namespace=item.metadata.namespace,
            status=item.status.phase or "Unknown",
            age=_calc_age(item.metadata.creation_timestamp),
            labels=item.metadata.labels or {},
            ready=f"{ready_count}/{len(containers)}",
            restarts=restarts,
            node=item.spec.node_name,
            ip=item.status.pod_ip,
            raw=item.to_dict() if hasattr(item, "to_dict") else {},
        )

    def list_nodes(self) -> list[NodeInfo]:
        """List all nodes with conditions and resources."""
        try:
            resp = self.v1.list_node()
        except Exception as e:
            raise RuntimeError(f"Failed to list nodes: {e}") from e

        nodes: list[NodeInfo] = []
        for item in resp.items:
            # Extract roles from labels
            roles = [
                k.split("/")[-1].replace("-master", "master").replace("-worker", "worker")
                for k in (item.metadata.labels or {})
                if k.startswith("node-role.kubernetes.io/")
            ]

            # Extract status
            conditions = [
                {"type": c.type, "status": c.status, "reason": c.reason}
                for c in (item.status.conditions or [])
            ]
            status_text = "Unknown"
            for c in conditions:
                if c["type"] == "Ready":
                    status_text = "Ready" if c["status"] == "True" else "NotReady"
                    break

            allocatable = item.status.allocatable or {}
            capacity = item.status.capacity or {}

            nodes.append(
                NodeInfo(
                    name=item.metadata.name,
                    age=_calc_age(item.metadata.creation_timestamp),
                    labels=item.metadata.labels or {},
                    roles=roles,
                    status_text=status_text,
                    version=item.status.node_info.kubelet_version if item.status.node_info else "",
                    cpu_allocatable=allocatable.get("cpu", ""),
                    memory_allocatable=allocatable.get("memory", ""),
                    cpu_capacity=capacity.get("cpu", ""),
                    memory_capacity=capacity.get("memory", ""),
                    conditions=conditions,
                    raw=item.to_dict() if hasattr(item, "to_dict") else {},
                )
            )
        return nodes

    def list_namespaces(self) -> list[K8sResource]:
        """List all namespaces."""
        try:
            resp = self.v1.list_namespace()
        except Exception as e:
            raise RuntimeError(f"Failed to list namespaces: {e}") from e

        return [
            K8sResource(
                kind="Namespace",
                name=item.metadata.name,
                status=item.status.phase or "Unknown",
                age=_calc_age(item.metadata.creation_timestamp),
                labels=item.metadata.labels or {},
            )
            for item in resp.items
        ]

    def list_services(self, namespace: str = "default") -> list[ServiceInfo]:
        """List services in namespace."""
        try:
            if namespace:
                resp = self.v1.list_namespaced_service(namespace)
            else:
                resp = self.v1.list_service_for_all_namespaces()
        except Exception as e:
            raise RuntimeError(f"Failed to list services: {e}") from e

        services: list[ServiceInfo] = []
        for item in resp.items:
            ports = [f"{p.port}/{p.protocol}" for p in (item.spec.ports or []) if p.port]
            external_ips = item.status.load_balancer.ingress or []
            ext_ip = external_ips[0].ip if external_ips else "<none>"

            services.append(
                ServiceInfo(
                    name=item.metadata.name,
                    namespace=item.metadata.namespace,
                    age=_calc_age(item.metadata.creation_timestamp),
                    labels=item.metadata.labels or {},
                    type=item.spec.type or "",
                    cluster_ip=item.spec.cluster_ip or "",
                    external_ip=ext_ip,
                    ports=ports,
                    raw=item.to_dict() if hasattr(item, "to_dict") else {},
                )
            )
        return services

    def list_configmaps(self, namespace: str = "default") -> list[K8sResource]:
        """List configmaps in namespace."""
        try:
            resp = self.v1.list_namespaced_config_map(namespace)
        except Exception as e:
            raise RuntimeError(f"Failed to list configmaps: {e}") from e

        return [
            K8sResource(
                kind="ConfigMap",
                name=item.metadata.name,
                namespace=item.metadata.namespace,
                age=_calc_age(item.metadata.creation_timestamp),
                labels=item.metadata.labels or {},
                data_keys=list(item.data.keys()) if item.data else [],
                raw=item.to_dict() if hasattr(item, "to_dict") else {},
            )
            for item in resp.items
        ]

    def describe_resource(
        self, kind: str, name: str, namespace: str = "default"
    ) -> dict[str, Any] | None:
        """Describe any resource by kind and name."""
        kind_lower = kind.lower()
        try:
            if kind_lower == "pod":
                obj = self.v1.read_namespaced_pod(name, namespace)
            elif kind_lower == "node":
                obj = self.v1.read_node(name)
            elif kind_lower == "namespace":
                obj = self.v1.read_namespace(name)
            elif kind_lower == "service":
                obj = self.v1.read_namespaced_service(name, namespace)
            elif kind_lower == "configmap":
                obj = self.v1.read_namespaced_config_map(name, namespace)
            elif kind_lower in ("deployment", "statefulset", "daemonset"):
                if kind_lower == "deployment":
                    obj = self.apps_v1.read_namespaced_deployment(name, namespace)
                elif kind_lower == "statefulset":
                    obj = self.apps_v1.read_namespaced_stateful_set(name, namespace)
                else:
                    obj = self.apps_v1.read_namespaced_daemon_set(name, namespace)
            else:
                return None
            return obj.to_dict() if hasattr(obj, "to_dict") else {}
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise RuntimeError(f"Failed to describe {kind}/{name}: {e}") from e

    def get_events(self, namespace: str = "", field_selector: str = "") -> list[EventInfo]:
        """Get events, optionally filtered by namespace and field selector."""
        try:
            if namespace:
                resp = self.v1.list_namespaced_event(namespace, field_selector=field_selector)
            else:
                resp = self.v1.list_event_for_all_namespaces(field_selector=field_selector)
        except Exception as e:
            raise RuntimeError(f"Failed to get events: {e}") from e

        events: list[EventInfo] = []
        for item in resp.items:
            involved = ""
            if item.involved_object:
                involved = f"{item.involved_object.kind}/{item.involved_object.name}"

            events.append(
                EventInfo(
                    type=item.type or "Normal",
                    reason=item.reason or "",
                    message=item.message or "",
                    source=item.source.component if item.source else "",
                    count=item.count or 1,
                    age=_calc_age(item.metadata.creation_timestamp),
                    involved_object=involved,
                )
            )
        # Sort by most recent first
        return events

    def get_pod_logs(
        self,
        name: str,
        namespace: str = "default",
        container: str | None = None,
        tail_lines: int = 100,
    ) -> LogEntry:
        """Fetch pod logs."""
        try:
            resp = self.v1.read_namespaced_pod_log(
                name,
                namespace,
                container=container,
                tail_lines=tail_lines,
            )
        except client.ApiException as e:
            raise RuntimeError(f"Failed to get logs for {name}: {e}") from e

        return LogEntry(
            pod_name=name,
            container=container,
            lines=resp.split("\n") if resp else [],
        )
