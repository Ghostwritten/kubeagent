"""Tests for Phase 08 — Memory System."""

from __future__ import annotations

from kubeagent.config.settings import KubeAgentConfig, MemoryConfig


class TestMemoryConfig:
    def test_defaults(self) -> None:
        config = MemoryConfig()
        assert config.enabled is True
        assert config.max_size_mb == 50
        assert config.audit_retention_days == 90
        assert "memory.db" in config.db_path

    def test_on_root_config(self) -> None:
        config = KubeAgentConfig()
        assert hasattr(config, "memory")
        assert config.memory.enabled is True
