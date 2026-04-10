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
