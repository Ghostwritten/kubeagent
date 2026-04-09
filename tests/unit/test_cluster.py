"""Tests for cluster context management."""

from kubeagent.infra.cluster import ClusterContext, ClusterInfo, KubeconfigManager


def test_cluster_info_dataclass() -> None:
    """ClusterInfo holds cluster details."""
    info = ClusterInfo(name="test", server="https://localhost:6443")
    assert info.name == "test"
    assert info.server == "https://localhost:6443"
    assert info.ca_data is None


def test_cluster_context_dataclass() -> None:
    """ClusterContext holds context details."""
    ctx = ClusterContext(name="test-ctx", cluster="test-cluster", user="test-user")
    assert ctx.name == "test-ctx"
    assert ctx.is_current is False
    assert ctx.namespace == "default"


def test_kubeconfig_manager_loads() -> None:
    """KubeconfigManager loads without error."""
    km = KubeconfigManager()
    # Should not crash even if no kubeconfig exists
    assert isinstance(km.get_contexts(), list)
    assert isinstance(km.get_clusters(), dict)


def test_kubeconfig_manager_invalid_path() -> None:
    """KubeconfigManager handles missing file gracefully."""
    km = KubeconfigManager("/nonexistent/kubeconfig")
    assert km.get_contexts() == []
    assert km.get_clusters() == {}


def test_context_exists_false() -> None:
    """context_exists returns False for missing context."""
    km = KubeconfigManager("/nonexistent/kubeconfig")
    assert km.context_exists("nonexistent") is False
