"""Tests for Phase 08 — Memory System."""

from __future__ import annotations

import tempfile
from pathlib import Path

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


from kubeagent.infra.storage import SQLiteStorage


class TestSQLiteStorage:
    def test_create_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = SQLiteStorage(db_path)
            assert db_path.exists()
            storage.close()

    def test_migration_creates_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SQLiteStorage(Path(tmpdir) / "test.db")
            tables = storage.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_names = [row[0] for row in tables]
            assert "preferences" in table_names
            assert "audit_log" in table_names
            storage.close()

    def test_user_version_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SQLiteStorage(Path(tmpdir) / "test.db")
            version = storage.fetchone("PRAGMA user_version")
            assert version is not None
            assert version[0] == 1
            storage.close()

    def test_execute_and_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SQLiteStorage(Path(tmpdir) / "test.db")
            storage.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?)",
                ("test_key", "test_value"),
            )
            row = storage.fetchone("SELECT value FROM preferences WHERE key = ?", ("test_key",))
            assert row is not None
            assert row[0] == "test_value"
            storage.close()

    def test_fetchall_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SQLiteStorage(Path(tmpdir) / "test.db")
            rows = storage.fetchall("SELECT * FROM preferences")
            assert rows == []
            storage.close()

    def test_idempotent_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = SQLiteStorage(db_path)
            storage.close()
            storage2 = SQLiteStorage(db_path)
            version = storage2.fetchone("PRAGMA user_version")
            assert version[0] == 1
            storage2.close()


from kubeagent.agent.memory import AuditEntry, AuditLogger


class TestAuditLogger:
    def _make_logger(self, tmpdir: str) -> AuditLogger:
        storage = SQLiteStorage(Path(tmpdir) / "test.db")
        return AuditLogger(storage)

    def test_log_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = self._make_logger(tmpdir)
            logger.log(
                cluster="prod",
                namespace="default",
                tool_name="delete_resource",
                args={"kind": "pod", "name": "nginx"},
                result="deleted",
                success=True,
            )
            entries = logger.query()
            assert len(entries) == 1
            assert entries[0].tool_name == "delete_resource"
            assert entries[0].cluster == "prod"
            assert entries[0].success is True
            logger._storage.close()

    def test_query_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = self._make_logger(tmpdir)
            for i in range(10):
                logger.log(
                    cluster="dev",
                    namespace="ns",
                    tool_name=f"tool_{i}",
                    args={},
                    result="ok",
                    success=True,
                )
            entries = logger.query(limit=3)
            assert len(entries) == 3
            logger._storage.close()

    def test_query_filter_by_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = self._make_logger(tmpdir)
            logger.log("c", "ns", "scale_resource", {}, "ok", True)
            logger.log("c", "ns", "delete_resource", {}, "ok", True)
            entries = logger.query(tool_name="scale_resource")
            assert len(entries) == 1
            assert entries[0].tool_name == "scale_resource"
            logger._storage.close()

    def test_redact_sensitive_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = self._make_logger(tmpdir)
            logger.log(
                cluster="prod",
                namespace="default",
                tool_name="apply_yaml",
                args={
                    "yaml_content": "apiVersion: v1",
                    "secret_data": "super-secret-123",
                    "token": "abc-token",
                    "Password": "hunter2",
                },
                result="applied",
                success=True,
            )
            entries = logger.query()
            import json

            args = json.loads(entries[0].args)
            assert args["yaml_content"] == "apiVersion: v1"
            assert args["secret_data"] == "[REDACTED]"
            assert args["token"] == "[REDACTED]"
            assert args["Password"] == "[REDACTED]"
            logger._storage.close()

    def test_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = self._make_logger(tmpdir)
            # Insert an old entry manually
            logger._storage.execute(
                "INSERT INTO audit_log (timestamp, tool_name, args, result, success) "
                "VALUES (datetime('now', '-100 days'), 'old_tool', '{}', 'ok', 1)"
            )
            logger.log("c", "ns", "new_tool", {}, "ok", True)
            logger.cleanup(retention_days=90)
            entries = logger.query()
            assert len(entries) == 1
            assert entries[0].tool_name == "new_tool"
            logger._storage.close()
