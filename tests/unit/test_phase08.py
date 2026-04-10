"""Tests for Phase 08 — Memory System."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from kubeagent.agent.deps import KubeAgentDeps
from kubeagent.agent.memory import (
    AuditEntry,
    AuditLogger,
    MemoryManager,
    PreferencesManager,
)
from kubeagent.agent.prompt_engine import build_system_prompt
from kubeagent.config.settings import KubeAgentConfig, MemoryConfig
from kubeagent.infra.storage import SQLiteStorage


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
            row = storage.fetchone(
                "SELECT value FROM preferences WHERE key = ?", ("test_key",)
            )
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
        import json

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


class TestPreferencesManager:
    def _make_prefs(self, tmpdir: str) -> PreferencesManager:
        storage = SQLiteStorage(Path(tmpdir) / "test.db")
        return PreferencesManager(storage)

    def test_set_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            prefs.set("language", "zh")
            assert prefs.get("language") == "zh"
            prefs._storage.close()

    def test_get_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            assert prefs.get("nonexistent") is None
            prefs._storage.close()

    def test_set_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            prefs.set("style", "rich")
            prefs.set("style", "markdown")
            assert prefs.get("style") == "markdown"
            prefs._storage.close()

    def test_get_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            prefs.set("a", "1")
            prefs.set("b", "2")
            all_prefs = prefs.get_all()
            assert all_prefs == {"a": "1", "b": "2"}
            prefs._storage.close()

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            prefs.set("key", "value")
            prefs.delete("key")
            assert prefs.get("key") is None
            prefs._storage.close()

    def test_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            prefs.set("a", "1")
            prefs.set("b", "2")
            prefs.clear()
            assert prefs.get_all() == {}
            prefs._storage.close()

    def test_to_prompt_section_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            assert prefs.to_prompt_section() == ""
            prefs._storage.close()

    def test_to_prompt_section_with_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs = self._make_prefs(tmpdir)
            prefs.set("language", "zh")
            prefs.set("output_style", "yaml")
            section = prefs.to_prompt_section()
            assert "language" in section
            assert "zh" in section
            assert "output_style" in section
            prefs._storage.close()


class TestMemoryManager:
    def test_creates_subsystems(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            mm = MemoryManager(config)
            assert mm.audit is not None
            assert mm.preferences is not None
            mm.close()

    def test_close_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            mm = MemoryManager(config)
            mm.close()
            mm.close()  # should not raise

    def test_cleanup_delegates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(
                db_path=str(Path(tmpdir) / "test.db"),
                audit_retention_days=90,
            )
            mm = MemoryManager(config)
            # Insert old entry
            mm.storage.execute(
                "INSERT INTO audit_log (timestamp, tool_name, args, result, success) "
                "VALUES (datetime('now', '-100 days'), 'old', '{}', 'ok', 1)"
            )
            mm.audit.log("c", "ns", "new", {}, "ok", True)
            mm.cleanup()
            entries = mm.audit.query()
            assert len(entries) == 1
            mm.close()


class TestDepsMemoryField:
    def test_default_none(self) -> None:
        deps = KubeAgentDeps(config=KubeAgentConfig())
        assert deps.memory is None

    def test_with_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            mm = MemoryManager(config)
            deps = KubeAgentDeps(config=KubeAgentConfig(), memory=mm)
            assert deps.memory is not None
            mm.close()


class TestCallToolAuditIntegration:
    def test_dangerous_tool_logs_audit_when_approved(self) -> None:
        """When auto_approve=True, dangerous tool executes and logs to audit."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.delete import DeleteResourceTool

        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            mm = MemoryManager(config)
            ctx = MagicMock()
            ctx.deps = KubeAgentDeps(
                config=KubeAgentConfig(),
                auto_approve=True,
                memory=mm,
            )
            _call_tool(
                DeleteResourceTool, ctx, kind="pod", name="test", namespace="default"
            )
            entries = mm.audit.query()
            assert len(entries) == 1
            assert entries[0].tool_name == "delete_resource"
            mm.close()

    def test_safe_tool_no_audit(self) -> None:
        """Safe tools should not produce audit entries."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.pods import GetPodsTool

        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            mm = MemoryManager(config)
            ctx = MagicMock()
            ctx.deps = KubeAgentDeps(config=KubeAgentConfig(), memory=mm)
            _call_tool(GetPodsTool, ctx, namespace="default")
            entries = mm.audit.query()
            assert len(entries) == 0
            mm.close()

    def test_no_memory_no_crash(self) -> None:
        """When memory is None, tool should still work without audit."""
        from kubeagent.agent.agent import _call_tool
        from kubeagent.tools.builtin.pods import GetPodsTool

        ctx = MagicMock()
        ctx.deps = KubeAgentDeps(config=KubeAgentConfig(), memory=None)
        result = _call_tool(GetPodsTool, ctx, namespace="default")
        assert "DENIED" not in result


class TestPromptEnginePreferences:
    def test_prompt_includes_memory_preferences(self) -> None:
        config = KubeAgentConfig()
        mem_prefs = "## User Preferences (from memory)\n- language: zh\n- output_style: yaml"
        prompt = build_system_prompt(config, memory_preferences=mem_prefs)
        assert "language: zh" in prompt
        assert "output_style: yaml" in prompt

    def test_prompt_without_preferences(self) -> None:
        config = KubeAgentConfig()
        prompt = build_system_prompt(config)
        assert "User Preferences (from memory)" not in prompt


class TestREPLMemoryCommands:
    def _make_repl(self, tmpdir: str):
        from kubeagent.cli.repl import KubeAgentREPL

        config = KubeAgentConfig(
            memory=MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
        )
        repl = KubeAgentREPL(config)
        repl._init_memory()
        return repl

    def test_remember_stores_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repl = self._make_repl(tmpdir)
            repl._handle_command("/remember I prefer YAML output")
            prefs = repl._memory.preferences.get_all()
            assert len(prefs) == 1
            assert "I prefer YAML output" in list(prefs.values())[0]
            repl._memory.close()

    def test_forget_deletes_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repl = self._make_repl(tmpdir)
            repl._handle_command("/remember I prefer YAML output")
            prefs = repl._memory.preferences.get_all()
            key = list(prefs.keys())[0]
            repl._handle_command(f"/forget {key}")
            assert repl._memory.preferences.get(key) is None
            repl._memory.close()

    def test_preferences_lists_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repl = self._make_repl(tmpdir)
            repl._handle_command("/remember test pref one")
            repl._handle_command("/remember test pref two")
            repl._handle_command("/preferences")
            repl._memory.close()


class TestRenderAuditTable:
    def test_render_no_crash(self) -> None:
        from kubeagent.cli.output import render_audit_table

        entries = [
            AuditEntry(
                id=1,
                timestamp="2026-04-10 12:00:00",
                cluster="prod",
                namespace="default",
                tool_name="delete_resource",
                args='{"kind": "pod"}',
                result="deleted",
                success=True,
            )
        ]
        render_audit_table(entries)


class TestMemorySystemIntegration:
    """End-to-end test: config -> storage -> audit + prefs -> prompt."""

    def test_full_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = KubeAgentConfig(
                memory=MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            )

            # MemoryManager
            mm = MemoryManager(config.memory)

            # Store preferences
            mm.preferences.set("language", "zh")
            mm.preferences.set("output_style", "yaml")

            # Preferences in prompt
            prefs_section = mm.preferences.to_prompt_section()
            prompt = build_system_prompt(config, memory_preferences=prefs_section)
            assert "language: zh" in prompt

            # Audit log
            mm.audit.log("prod", "default", "delete_resource", {"kind": "pod"}, "ok", True)
            entries = mm.audit.query()
            assert len(entries) == 1

            # Cleanup + close
            mm.cleanup()
            mm.close()

            # Reopen — data persists
            mm2 = MemoryManager(config.memory)
            assert mm2.preferences.get("language") == "zh"
            assert len(mm2.audit.query()) == 1
            mm2.close()
