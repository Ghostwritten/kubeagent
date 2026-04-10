# Phase 08 — Memory System Design

> Date: 2026-04-10
> Scope: Storage Layer + Audit Log + User Preferences (core subset of Phase 08 plan)
> Deferred: Cluster profiles, fault knowledge base (future Phase)

---

## 1. Storage Layer (`infra/storage.py`)

SQLite-based persistence using Python's built-in `sqlite3` module. Zero external dependencies.

### SQLiteStorage class

```
SQLiteStorage
├── __init__(db_path: Path | str)   # Default: ~/.kubeagent/memory.db
├── _connect() -> Connection        # Lazy connection, WAL mode
├── _migrate()                      # PRAGMA user_version based versioning
├── execute(sql, params) -> Cursor
├── fetchall(sql, params) -> list[Row]
├── fetchone(sql, params) -> Row | None
└── close()
```

### Schema (v1)

```sql
CREATE TABLE preferences (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  TEXT NOT NULL DEFAULT (datetime('now')),
    cluster    TEXT,
    namespace  TEXT,
    tool_name  TEXT NOT NULL,
    args       TEXT,          -- JSON, redacted
    result     TEXT,
    success    INTEGER NOT NULL DEFAULT 1
);
```

### Migration strategy

- `PRAGMA user_version` starts at 0
- `_migrate()` checks current version, runs incremental SQL for each version step
- Future Phases append new versions (e.g., v2 adds cluster_profiles table)

---

## 2. Audit Log (`agent/memory.py` — AuditLogger)

Append-only log of all mutating operations (SENSITIVE/DANGEROUS tools).

### AuditLogger class

```
AuditLogger
├── __init__(storage: SQLiteStorage)
├── log(cluster, namespace, tool_name, args, result, success)
├── query(limit=50, cluster=None, tool_name=None) -> list[AuditEntry]
├── cleanup(retention_days: int = 90)
└── _redact(args: dict) -> dict
```

### AuditEntry dataclass

```python
@dataclass
class AuditEntry:
    id: int
    timestamp: str
    cluster: str | None
    namespace: str | None
    tool_name: str
    args: str        # JSON
    result: str
    success: bool
```

### Redaction rules

`_redact()` scans args dict keys (case-insensitive). Keys containing any of `secret`, `token`, `password`, `credential` have their values replaced with `"[REDACTED]"`.

### Integration point

In `agent.py` `_call_tool()`: after tool execution (success or failure), if `security_level != SAFE`, call `audit_logger.log()`.

### REPL command

`/audit` — displays recent N audit entries as a Rich table.

---

## 3. User Preferences (`agent/memory.py` — PreferencesManager)

Key-value store for user preferences, persisted across sessions.

### PreferencesManager class

```
PreferencesManager
├── __init__(storage: SQLiteStorage)
├── set(key: str, value: str)
├── get(key: str) -> str | None
├── get_all() -> dict[str, str]
├── delete(key: str)
├── clear()
└── to_prompt_section() -> str
```

### Predefined keys (convention, not enforced)

- `output_style` — rich / markdown / mixed
- `language` — en / zh / auto
- `favorite_namespaces` — comma-separated

Users can also store free-form keys.

### `/remember` implementation

First version stores raw text. Key = hashlib.md5 of content, truncated to 8 chars. No LLM extraction — YAGNI.

### Integration points

- **Prompt Engine**: `build_system_prompt()` accepts optional preferences section from `preferences.to_prompt_section()`
- **REPL commands**:
  - `/remember <text>` — store preference
  - `/forget <key>` — delete preference
  - `/preferences` — list all preferences

---

## 4. Configuration

### MemoryConfig (added to settings.py)

```python
class MemoryConfig(BaseModel):
    enabled: bool = True
    db_path: str = str(Path.home() / ".kubeagent" / "memory.db")
    max_size_mb: int = 50
    audit_retention_days: int = 90
```

Added as `memory: MemoryConfig` field on `KubeAgentConfig`.

---

## 5. MemoryManager — Unified Facade

```
MemoryManager
├── __init__(config: MemoryConfig)
├── storage: SQLiteStorage
├── audit: AuditLogger
├── preferences: PreferencesManager
├── close()
└── cleanup()
```

Single entry point for all memory operations. Created once in REPL, passed via `KubeAgentDeps.memory`.

---

## 6. Integration Flow

```
REPL.start()
  ├── MemoryManager(config.memory)          # init storage + tables
  ├── preferences.to_prompt_section()       # inject into system prompt
  ├── _handle_query()
  │     └── _call_tool()
  │           └── audit.log()               # record non-SAFE ops
  ├── /audit    → audit.query()             # REPL commands
  ├── /remember → preferences.set()
  ├── /forget   → preferences.delete()
  ├── /preferences → preferences.get_all()
  └── REPL.exit → memory.close()
```

---

## 7. Files

| File | Action | Description |
|------|--------|-------------|
| `infra/storage.py` | Create | SQLiteStorage with migration |
| `agent/memory.py` | Create | MemoryManager, AuditLogger, PreferencesManager |
| `config/settings.py` | Modify | Add MemoryConfig |
| `agent/deps.py` | Modify | Add memory field |
| `agent/agent.py` | Modify | Audit logging in _call_tool |
| `agent/prompt_engine.py` | Modify | Inject preferences into prompt |
| `cli/repl.py` | Modify | Init memory, add 4 commands |
| `cli/output.py` | Modify | Add render_audit_table |
| `tests/unit/test_phase08.py` | Create | Tests for all components |

---

## 8. Security Constraints

- Secrets, tokens, passwords are never stored in audit_log (redacted)
- `memory.db` is user-local (`~/.kubeagent/`), not project-local
- `max_size_mb` config prevents unbounded growth
- `audit_retention_days` auto-cleans old entries

---

## 9. Out of Scope (deferred)

- Cluster profile memory (auto-populate topology)
- Fault knowledge base (symptom → root cause)
- Session context memory (within-conversation, already handled by Pydantic AI message_history)
- LLM-powered preference extraction from `/remember`
