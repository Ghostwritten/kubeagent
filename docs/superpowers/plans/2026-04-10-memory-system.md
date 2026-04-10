# Phase 08 — Memory System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent memory (SQLite) to KubeAgent — audit logging for mutating operations and user preference storage across sessions.

**Architecture:** Three-layer design: `SQLiteStorage` (infra) handles DB connection/migration, `AuditLogger` + `PreferencesManager` (agent/memory.py) provide domain logic, `MemoryManager` is the unified facade injected via `KubeAgentDeps`. Integration touches `_call_tool()` for audit and `build_system_prompt()` for preferences.

**Tech Stack:** Python `sqlite3` stdlib, existing Pydantic config, Rich tables for `/audit` display.

**Spec:** `docs/superpowers/specs/2026-04-10-memory-system-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/kubeagent/infra/storage.py` | Create | SQLiteStorage — connection, migration, query helpers |
| `src/kubeagent/agent/memory.py` | Create | MemoryManager, AuditLogger, PreferencesManager |
| `src/kubeagent/config/settings.py` | Modify | Add MemoryConfig class + field on KubeAgentConfig |
| `src/kubeagent/agent/deps.py` | Modify | Add `memory: MemoryManager \| None` field |
| `src/kubeagent/agent/agent.py` | Modify | Audit logging in `_call_tool()` |
| `src/kubeagent/agent/prompt_engine.py` | Modify | Accept + inject user preferences section |
| `src/kubeagent/cli/repl.py` | Modify | Init memory, add `/audit`, `/remember`, `/forget`, `/preferences` |
| `src/kubeagent/cli/output.py` | Modify | Add `render_audit_table()` + `render_preferences()` |
| `tests/unit/test_phase08.py` | Create | All tests |

---

### Task 1: MemoryConfig + settings

**Files:**
- Modify: `src/kubeagent/config/settings.py:30-44`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_phase08.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_phase08.py::TestMemoryConfig -v`
Expected: FAIL — `MemoryConfig` not found

- [ ] **Step 3: Write minimal implementation**

Add to `src/kubeagent/config/settings.py` before `KubeAgentConfig`:

```python
class MemoryConfig(BaseModel):
    """Memory system configuration."""

    enabled: bool = True
    db_path: str = str(Path.home() / ".kubeagent" / "memory.db")
    max_size_mb: int = 50
    audit_retention_days: int = 90
```

Add field to `KubeAgentConfig`:

```python
class KubeAgentConfig(BaseModel):
    """Root configuration for KubeAgent."""

    model: ModelConfig = Field(default_factory=ModelConfig)
    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    initialized: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_phase08.py::TestMemoryConfig -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/config/settings.py tests/unit/test_phase08.py
git commit -m "feat(phase08): add MemoryConfig to settings"
```

---

### Task 2: SQLiteStorage

**Files:**
- Create: `src/kubeagent/infra/storage.py`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_phase08.py`:

```python
import tempfile
from pathlib import Path

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
            # Reopen — should not fail on existing tables
            storage2 = SQLiteStorage(db_path)
            version = storage2.fetchone("PRAGMA user_version")
            assert version[0] == 1
            storage2.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestSQLiteStorage -v`
Expected: FAIL — `storage` module not found

- [ ] **Step 3: Write implementation**

Create `src/kubeagent/infra/storage.py`:

```python
"""SQLite storage layer for KubeAgent memory system."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_MIGRATIONS: dict[int, list[str]] = {
    1: [
        """CREATE TABLE IF NOT EXISTS preferences (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL DEFAULT (datetime('now')),
            cluster    TEXT,
            namespace  TEXT,
            tool_name  TEXT NOT NULL,
            args       TEXT,
            result     TEXT,
            success    INTEGER NOT NULL DEFAULT 1
        )""",
    ],
}

LATEST_VERSION = max(_MIGRATIONS)


class SQLiteStorage:
    """SQLite-based persistent storage for KubeAgent."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._connect()
        self._migrate()

    def _connect(self) -> None:
        """Open the database connection with WAL mode."""
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def _migrate(self) -> None:
        """Run pending migrations based on PRAGMA user_version."""
        assert self._conn is not None
        current = self._conn.execute("PRAGMA user_version").fetchone()[0]
        for version in range(current + 1, LATEST_VERSION + 1):
            for sql in _MIGRATIONS[version]:
                self._conn.execute(sql)
            self._conn.execute(f"PRAGMA user_version = {version}")
        self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL statement and commit."""
        assert self._conn is not None
        cursor = self._conn.execute(sql, params)
        self._conn.commit()
        return cursor

    def fetchall(self, sql: str, params: tuple = ()) -> list:
        """Execute a query and return all rows."""
        assert self._conn is not None
        return self._conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()):
        """Execute a query and return a single row."""
        assert self._conn is not None
        return self._conn.execute(sql, params).fetchone()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestSQLiteStorage -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/infra/storage.py tests/unit/test_phase08.py
git commit -m "feat(phase08): add SQLiteStorage with migration support"
```

---

### Task 3: AuditLogger

**Files:**
- Create: `src/kubeagent/agent/memory.py`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_phase08.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestAuditLogger -v`
Expected: FAIL — `AuditLogger` not found

- [ ] **Step 3: Write implementation**

Create `src/kubeagent/agent/memory.py`:

```python
"""Memory system — AuditLogger, PreferencesManager, MemoryManager."""

from __future__ import annotations

import json
from dataclasses import dataclass

from kubeagent.infra.storage import SQLiteStorage

# Keys whose values should be redacted in audit logs
_SENSITIVE_PATTERNS = ("secret", "token", "password", "credential")


@dataclass
class AuditEntry:
    """A single audit log entry."""

    id: int
    timestamp: str
    cluster: str | None
    namespace: str | None
    tool_name: str
    args: str
    result: str
    success: bool


class AuditLogger:
    """Append-only audit log for mutating operations."""

    def __init__(self, storage: SQLiteStorage) -> None:
        self._storage = storage

    def log(
        self,
        cluster: str | None,
        namespace: str | None,
        tool_name: str,
        args: dict,
        result: str,
        success: bool,
    ) -> None:
        """Record a mutating operation."""
        redacted = self._redact(args)
        self._storage.execute(
            "INSERT INTO audit_log (cluster, namespace, tool_name, args, result, success) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (cluster, namespace, tool_name, json.dumps(redacted), result, int(success)),
        )

    def query(
        self,
        limit: int = 50,
        cluster: str | None = None,
        tool_name: str | None = None,
    ) -> list[AuditEntry]:
        """Query audit log entries."""
        sql = "SELECT id, timestamp, cluster, namespace, tool_name, args, result, success FROM audit_log"
        conditions: list[str] = []
        params: list = []

        if cluster is not None:
            conditions.append("cluster = ?")
            params.append(cluster)
        if tool_name is not None:
            conditions.append("tool_name = ?")
            params.append(tool_name)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = self._storage.fetchall(sql, tuple(params))
        return [
            AuditEntry(
                id=row[0],
                timestamp=row[1],
                cluster=row[2],
                namespace=row[3],
                tool_name=row[4],
                args=row[5],
                result=row[6],
                success=bool(row[7]),
            )
            for row in rows
        ]

    def cleanup(self, retention_days: int = 90) -> int:
        """Remove entries older than retention_days. Returns count deleted."""
        cursor = self._storage.execute(
            "DELETE FROM audit_log WHERE timestamp < datetime('now', ?)",
            (f"-{retention_days} days",),
        )
        return cursor.rowcount

    def _redact(self, args: dict) -> dict:
        """Replace sensitive values with [REDACTED]."""
        redacted = {}
        for key, value in args.items():
            key_lower = key.lower()
            if any(p in key_lower for p in _SENSITIVE_PATTERNS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = value
        return redacted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestAuditLogger -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/agent/memory.py tests/unit/test_phase08.py
git commit -m "feat(phase08): add AuditLogger with redaction and cleanup"
```

---

### Task 4: PreferencesManager

**Files:**
- Modify: `src/kubeagent/agent/memory.py`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_phase08.py`:

```python
from kubeagent.agent.memory import PreferencesManager


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestPreferencesManager -v`
Expected: FAIL — `PreferencesManager` not found

- [ ] **Step 3: Write implementation**

Append to `src/kubeagent/agent/memory.py`:

```python
class PreferencesManager:
    """Key-value store for user preferences."""

    def __init__(self, storage: SQLiteStorage) -> None:
        self._storage = storage

    def set(self, key: str, value: str) -> None:
        """Set a preference (insert or update)."""
        self._storage.execute(
            "INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
            (key, value),
        )

    def get(self, key: str) -> str | None:
        """Get a single preference value."""
        row = self._storage.fetchone(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        )
        return row[0] if row else None

    def get_all(self) -> dict[str, str]:
        """Get all preferences as a dict."""
        rows = self._storage.fetchall("SELECT key, value FROM preferences ORDER BY key")
        return {row[0]: row[1] for row in rows}

    def delete(self, key: str) -> None:
        """Delete a single preference."""
        self._storage.execute("DELETE FROM preferences WHERE key = ?", (key,))

    def clear(self) -> None:
        """Delete all preferences."""
        self._storage.execute("DELETE FROM preferences")

    def to_prompt_section(self) -> str:
        """Format preferences as a system prompt section."""
        prefs = self.get_all()
        if not prefs:
            return ""
        lines = ["## User Preferences (from memory)"]
        for key, value in prefs.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestPreferencesManager -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/agent/memory.py tests/unit/test_phase08.py
git commit -m "feat(phase08): add PreferencesManager with prompt injection"
```

---

### Task 5: MemoryManager facade + deps integration

**Files:**
- Modify: `src/kubeagent/agent/memory.py`
- Modify: `src/kubeagent/agent/deps.py`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_phase08.py`:

```python
from kubeagent.agent.memory import MemoryManager


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
        from kubeagent.agent.deps import KubeAgentDeps

        deps = KubeAgentDeps(config=KubeAgentConfig())
        assert deps.memory is None

    def test_with_memory(self) -> None:
        from kubeagent.agent.deps import KubeAgentDeps

        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            mm = MemoryManager(config)
            deps = KubeAgentDeps(config=KubeAgentConfig(), memory=mm)
            assert deps.memory is not None
            mm.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestMemoryManager tests/unit/test_phase08.py::TestDepsMemoryField -v`
Expected: FAIL — `MemoryManager` not found, deps missing `memory`

- [ ] **Step 3: Write implementation**

Append to `src/kubeagent/agent/memory.py`:

```python
from kubeagent.config.settings import MemoryConfig


class MemoryManager:
    """Unified facade for all memory subsystems."""

    def __init__(self, config: MemoryConfig) -> None:
        self._config = config
        self.storage = SQLiteStorage(config.db_path)
        self.audit = AuditLogger(self.storage)
        self.preferences = PreferencesManager(self.storage)

    def cleanup(self) -> None:
        """Run maintenance: expire old audit entries."""
        self.audit.cleanup(retention_days=self._config.audit_retention_days)

    def close(self) -> None:
        """Close the storage connection."""
        self.storage.close()
```

Update `src/kubeagent/agent/deps.py`:

```python
"""Core agent module for KubeAgent."""

from __future__ import annotations

from dataclasses import dataclass, field

from kubeagent.config.settings import KubeAgentConfig


@dataclass
class KubeAgentDeps:
    """Dependency injection container for the KubeAgent."""

    config: KubeAgentConfig
    auto_approve: bool = False
    dry_run: bool = False
    memory: object | None = None  # MemoryManager, typed as object to avoid circular import
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestMemoryManager tests/unit/test_phase08.py::TestDepsMemoryField -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/agent/memory.py src/kubeagent/agent/deps.py tests/unit/test_phase08.py
git commit -m "feat(phase08): add MemoryManager facade and deps integration"
```

---

### Task 6: Audit logging in _call_tool

**Files:**
- Modify: `src/kubeagent/agent/agent.py:229-270`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_phase08.py`:

```python
from unittest.mock import MagicMock

from kubeagent.agent.deps import KubeAgentDeps


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
            _call_tool(DeleteResourceTool, ctx, kind="pod", name="test", namespace="default")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestCallToolAuditIntegration -v`
Expected: FAIL — first test fails because `_call_tool` doesn't log to audit yet

- [ ] **Step 3: Modify `_call_tool` in `src/kubeagent/agent/agent.py`**

Replace the `_call_tool` function (around line 229):

```python
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
        _audit_failure(tool, deps, kwargs, str(e))
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestCallToolAuditIntegration -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run all existing tests to verify no regressions**

Run: `uv run pytest tests/ -x --tb=short`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/kubeagent/agent/agent.py tests/unit/test_phase08.py
git commit -m "feat(phase08): integrate audit logging into _call_tool"
```

---

### Task 7: Prompt engine preferences injection

**Files:**
- Modify: `src/kubeagent/agent/prompt_engine.py:96-128`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_phase08.py`:

```python
from kubeagent.agent.prompt_engine import build_system_prompt


class TestPromptEnginePreferences:
    def test_prompt_includes_memory_preferences(self) -> None:
        config = KubeAgentConfig()
        prompt = build_system_prompt(
            config,
            memory_preferences="## User Preferences (from memory)\n- language: zh\n- output_style: yaml",
        )
        assert "language: zh" in prompt
        assert "output_style: yaml" in prompt

    def test_prompt_without_preferences(self) -> None:
        config = KubeAgentConfig()
        prompt = build_system_prompt(config)
        assert "User Preferences (from memory)" not in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestPromptEnginePreferences -v`
Expected: FAIL — `build_system_prompt` doesn't accept `memory_preferences`

- [ ] **Step 3: Modify `build_system_prompt` in `src/kubeagent/agent/prompt_engine.py`**

Update the function signature and body:

```python
def build_system_prompt(
    config: KubeAgentConfig,
    cluster_name: str | None = None,
    namespace: str | None = None,
    server: str | None = None,
    kubeagent_md_path: Path | None = None,
    memory_preferences: str | None = None,
) -> str:
    """Compose the full system prompt from all sources.

    Order (later sections override earlier ones):
    1. Base prompt (hardcoded)
    2. Cluster context (dynamic)
    3. User preferences (from config)
    4. Memory preferences (from SQLite)
    5. KUBEAGENT.md rules (user-defined)
    """
    sections: list[str] = [_BASE_PROMPT]

    # Cluster context
    cluster_ctx = build_cluster_context(cluster_name, namespace, server)
    if cluster_ctx:
        sections.append(cluster_ctx)

    # User preferences from config
    sections.append(build_preferences_section(config))

    # Memory preferences
    if memory_preferences:
        sections.append(memory_preferences)

    # KUBEAGENT.md rules
    kubeagent_md = load_kubeagent_md(kubeagent_md_path)
    if kubeagent_md:
        sections.append("## Project Rules (from KUBEAGENT.md)\n")
        sections.append(kubeagent_md)

    return "\n\n".join(sections)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestPromptEnginePreferences tests/unit/test_phase07.py -v`
Expected: All pass (no regression in Phase 07 tests)

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/agent/prompt_engine.py tests/unit/test_phase08.py
git commit -m "feat(phase08): inject memory preferences into system prompt"
```

---

### Task 8: REPL commands + output helpers

**Files:**
- Modify: `src/kubeagent/cli/repl.py`
- Modify: `src/kubeagent/cli/output.py`
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_phase08.py`:

```python
import hashlib


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

    def test_preferences_lists_all(self, capsys) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repl = self._make_repl(tmpdir)
            repl._handle_command("/remember test pref one")
            repl._handle_command("/remember test pref two")
            repl._handle_command("/preferences")
            # Should not raise
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
        # Should not raise
        render_audit_table(entries)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_phase08.py::TestREPLMemoryCommands tests/unit/test_phase08.py::TestRenderAuditTable -v`
Expected: FAIL

- [ ] **Step 3a: Add output helpers to `src/kubeagent/cli/output.py`**

Add before `render_spinner`:

```python
def render_audit_table(entries: list) -> None:
    """Render audit log entries as a Rich table."""
    from kubeagent.agent.memory import AuditEntry

    table = Table(title="Audit Log")
    table.add_column("ID", style="dim")
    table.add_column("Timestamp")
    table.add_column("Tool", style="cyan")
    table.add_column("Namespace")
    table.add_column("Result")
    table.add_column("OK", justify="center")

    for entry in entries:
        ok = "[green]Y[/green]" if entry.success else "[red]N[/red]"
        table.add_row(
            str(entry.id),
            entry.timestamp,
            entry.tool_name,
            entry.namespace or "-",
            (entry.result or "")[:40],
            ok,
        )
    console.print(table)


def render_preferences(prefs: dict[str, str]) -> None:
    """Render user preferences."""
    if not prefs:
        console.print("[dim]No saved preferences.[/dim]")
        return
    table = Table(title="Preferences")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    for key, value in prefs.items():
        table.add_row(key, value)
    console.print(table)
```

- [ ] **Step 3b: Add memory init and commands to `src/kubeagent/cli/repl.py`**

Add import at top:

```python
import hashlib
```

Add `_init_memory` method to `KubeAgentREPL`:

```python
def _init_memory(self) -> None:
    """Initialize the memory system."""
    if self.config.memory.enabled:
        from kubeagent.agent.memory import MemoryManager

        self._memory = MemoryManager(self.config.memory)
    else:
        self._memory = None
```

Update `__init__` to add `self._memory = None`.

Update `start()` to call `self._init_memory()` after cluster detection, and `self._memory.close()` before exit.

Update `_init_agent` to pass memory preferences to `build_system_prompt`:

```python
def _init_agent(self) -> None:
    """Initialize the agent lazily with dynamic prompt."""
    if self._agent is None:
        memory_prefs = None
        if self._memory is not None:
            memory_prefs = self._memory.preferences.to_prompt_section() or None
        system_prompt = build_system_prompt(
            config=self.config,
            cluster_name=self._cluster_name,
            namespace=self._namespace,
            server=self._server,
            memory_preferences=memory_prefs,
        )
        self._agent = create_agent(self.config, system_prompt=system_prompt)
```

Update `_handle_query` to pass memory to deps:

```python
deps = KubeAgentDeps(
    config=self.config,
    auto_approve=self.auto_approve,
    dry_run=self.dry_run,
    memory=self._memory,
)
```

Add command handlers in `_handle_command`:

```python
elif cmd == "/audit":
    self._handle_audit()
elif cmd == "/preferences":
    self._handle_preferences()
elif cmd.startswith("/remember "):
    self._handle_remember(command[10:].strip())
elif cmd.startswith("/forget "):
    self._handle_forget(command[8:].strip())
```

Add the handler methods:

```python
def _handle_audit(self) -> None:
    """Show recent audit log entries."""
    if self._memory is None:
        render_error("Memory system is disabled.")
        return
    from kubeagent.cli.output import render_audit_table

    entries = self._memory.audit.query(limit=20)
    if not entries:
        console.print("[dim]No audit entries.[/dim]")
    else:
        render_audit_table(entries)

def _handle_preferences(self) -> None:
    """Show all saved preferences."""
    if self._memory is None:
        render_error("Memory system is disabled.")
        return
    from kubeagent.cli.output import render_preferences

    render_preferences(self._memory.preferences.get_all())

def _handle_remember(self, text: str) -> None:
    """Save a user preference."""
    if self._memory is None:
        render_error("Memory system is disabled.")
        return
    if not text:
        render_error("Usage: /remember <text>")
        return
    key = hashlib.md5(text.encode()).hexdigest()[:8]
    self._memory.preferences.set(key, text)
    console.print(f"[dim]Saved (key={key}): {text}[/dim]")

def _handle_forget(self, key: str) -> None:
    """Delete a preference by key."""
    if self._memory is None:
        render_error("Memory system is disabled.")
        return
    if not key:
        render_error("Usage: /forget <key>")
        return
    self._memory.preferences.delete(key)
    console.print(f"[dim]Deleted preference: {key}[/dim]")
```

Update `render_help` in `output.py` to include new commands:

```python
console.print("  [cyan]/audit[/cyan]      Show recent operations audit log")
console.print("  [cyan]/remember[/cyan]  Save a preference (e.g., /remember I prefer YAML)")
console.print("  [cyan]/forget[/cyan]    Delete a preference by key")
console.print("  [cyan]/preferences[/cyan] List all saved preferences")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_phase08.py::TestREPLMemoryCommands tests/unit/test_phase08.py::TestRenderAuditTable -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kubeagent/cli/repl.py src/kubeagent/cli/output.py tests/unit/test_phase08.py
git commit -m "feat(phase08): add REPL memory commands and audit table rendering"
```

---

### Task 9: Full integration test + cleanup

**Files:**
- Test: `tests/unit/test_phase08.py`

- [ ] **Step 1: Write the full integration test**

Append to `tests/unit/test_phase08.py`:

```python
class TestMemorySystemIntegration:
    """End-to-end test: config → storage → audit + prefs → prompt."""

    def test_full_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Config
            config = KubeAgentConfig(
                memory=MemoryConfig(db_path=str(Path(tmpdir) / "test.db"))
            )

            # 2. MemoryManager
            mm = MemoryManager(config.memory)

            # 3. Store preferences
            mm.preferences.set("language", "zh")
            mm.preferences.set("output_style", "yaml")

            # 4. Preferences in prompt
            prefs_section = mm.preferences.to_prompt_section()
            prompt = build_system_prompt(config, memory_preferences=prefs_section)
            assert "language: zh" in prompt

            # 5. Audit log
            mm.audit.log("prod", "default", "delete_resource", {"kind": "pod"}, "ok", True)
            entries = mm.audit.query()
            assert len(entries) == 1

            # 6. Cleanup + close
            mm.cleanup()
            mm.close()

            # 7. Reopen — data persists
            mm2 = MemoryManager(config.memory)
            assert mm2.preferences.get("language") == "zh"
            assert len(mm2.audit.query()) == 1
            mm2.close()
```

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest tests/ -x --tb=short`
Expected: All tests pass (previous 155 + new Phase 08 tests)

- [ ] **Step 3: Run linting**

Run: `uv run ruff check src/kubeagent/ tests/`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_phase08.py
git commit -m "feat(phase08): add full integration test for memory system"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | MemoryConfig + settings | 2 |
| 2 | SQLiteStorage | 6 |
| 3 | AuditLogger | 5 |
| 4 | PreferencesManager | 8 |
| 5 | MemoryManager + deps | 5 |
| 6 | Audit in _call_tool | 3 |
| 7 | Prompt engine preferences | 2 |
| 8 | REPL commands + output | 4 |
| 9 | Integration test | 1 |
| **Total** | | **36** |
