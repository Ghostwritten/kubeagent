"""Memory system — AuditLogger, PreferencesManager, MemoryManager."""

from __future__ import annotations

import json
from dataclasses import dataclass

from kubeagent.config.settings import MemoryConfig
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
        sql = (
            "SELECT id, timestamp, cluster, namespace, tool_name, args, result, success "
            "FROM audit_log"
        )
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
