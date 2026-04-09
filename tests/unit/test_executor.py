"""Tests for K8s executor data models and helpers."""

from kubeagent.infra.executor import (
    EventInfo,
    K8sResource,
    LogEntry,
    NodeInfo,
    PodInfo,
    SecurityLevel,
    ServiceInfo,
    _calc_age,
    _labels_match,
)


class TestSecurityLevel:
    def test_security_level_values(self) -> None:
        assert SecurityLevel.SAFE == "safe"
        assert SecurityLevel.SENSITIVE == "sensitive"
        assert SecurityLevel.DANGEROUS == "dangerous"


class TestCalcAge:
    def test_none_timestamp(self) -> None:
        assert _calc_age(None) == "unknown"

    def test_empty_timestamp(self) -> None:
        assert _calc_age("") == "unknown"

    def test_invalid_timestamp(self) -> None:
        assert _calc_age("not-a-date") == "unknown"

    def test_days_format(self) -> None:
        # Timestamps from K8s are in ISO 8601 format
        # Create a timestamp from 5 days ago
        from datetime import UTC, datetime, timedelta

        five_days_ago = datetime.now(UTC) - timedelta(days=5)
        ts = five_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ").replace("+00:00", "Z")
        age = _calc_age(ts)
        assert age.startswith("5d")


class TestLabelsMatch:
    def test_no_selector(self) -> None:
        labels = {"app": "nginx", "env": "prod"}
        assert _labels_match(labels, None) is True

    def test_empty_selector(self) -> None:
        labels = {"app": "nginx"}
        assert _labels_match(labels, {}) is True

    def test_match_single(self) -> None:
        labels = {"app": "nginx", "env": "prod"}
        assert _labels_match(labels, {"app": "nginx"}) is True

    def test_match_multiple(self) -> None:
        labels = {"app": "nginx", "env": "prod"}
        assert _labels_match(labels, {"app": "nginx", "env": "prod"}) is True

    def test_mismatch(self) -> None:
        labels = {"app": "nginx", "env": "staging"}
        assert _labels_match(labels, {"app": "nginx", "env": "prod"}) is False

    def test_missing_label(self) -> None:
        labels = {"app": "nginx"}
        assert _labels_match(labels, {"app": "nginx", "env": "prod"}) is False


class TestK8sResource:
    def test_default_values(self) -> None:
        r = K8sResource(kind="Pod", name="test-pod")
        assert r.kind == "Pod"
        assert r.name == "test-pod"
        assert r.namespace is None
        assert r.status is None
        assert r.age is None
        assert r.labels == {}
        assert r.annotations == {}
        assert r.raw == {}


class TestPodInfo:
    def test_default_values(self) -> None:
        p = PodInfo(name="my-pod", namespace="default")
        assert p.kind == "Pod"
        assert p.ready == "0/0"
        assert p.restarts == 0
        assert p.node is None
        assert p.ip is None
        assert p.containers == []


class TestNodeInfo:
    def test_default_values(self) -> None:
        n = NodeInfo(name="node-1")
        assert n.kind == "Node"
        assert n.roles == []
        assert n.status_text == "Unknown"
        assert n.version == ""
        assert n.conditions == []


class TestServiceInfo:
    def test_default_values(self) -> None:
        s = ServiceInfo(name="svc-1", namespace="default")
        assert s.kind == "Service"
        assert s.type == ""
        assert s.cluster_ip == ""
        assert s.external_ip == ""
        assert s.ports == []


class TestEventInfo:
    def test_fields(self) -> None:
        e = EventInfo(
            type="Normal",
            reason="Started",
            message="Container started",
            source="kubelet",
            count=1,
            age="5m",
            involved_object="Pod/nginx-123",
        )
        assert e.type == "Normal"
        assert e.reason == "Started"
        assert e.count == 1


class TestLogEntry:
    def test_fields(self) -> None:
        log = LogEntry(pod_name="nginx-123", container="nginx", lines=["line1", "line2"])
        assert log.pod_name == "nginx-123"
        assert log.container == "nginx"
        assert log.lines == ["line1", "line2"]
