"""SQLite-backed storage for LoopFlow iterations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from loopflow.models import AgentType, Iteration


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS iterations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_type TEXT NOT NULL DEFAULT 'manual',
    prompt TEXT NOT NULL,
    files_changed TEXT NOT NULL DEFAULT '[]',
    error_message TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    tokens_used INTEGER,
    duration_seconds REAL,
    timestamp TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_iterations_session ON iterations(session_id);
CREATE INDEX IF NOT EXISTS idx_iterations_timestamp ON iterations(timestamp);
"""


class Storage:
    """SQLite storage backend for LoopFlow."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path.home() / ".loopflow"
            data_dir.mkdir(exist_ok=True)
            self.db_path = str(data_dir / "loopflow.db")
        else:
            self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(DB_SCHEMA)

    def add_iteration(self, iteration: Iteration) -> str:
        """Store an iteration and return its ID."""
        self._conn.execute(
            """INSERT OR REPLACE INTO iterations
               (id, session_id, agent_type, prompt, files_changed,
                error_message, success, tokens_used, duration_seconds, timestamp, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                iteration.id,
                iteration.session_id,
                iteration.agent_type.value,
                iteration.prompt,
                json.dumps(iteration.files_changed),
                iteration.error_message,
                1 if iteration.success else 0,
                iteration.tokens_used,
                iteration.duration_seconds,
                iteration.timestamp,
                iteration.notes,
            ),
        )
        self._conn.commit()
        return iteration.id

    def get_iterations(self, session_id: Optional[str] = None, limit: int = 50) -> list[Iteration]:
        """Retrieve iterations, optionally filtered by session."""
        query = "SELECT * FROM iterations"
        params: list = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        iterations = []
        for row in rows:
            iterations.append(
                Iteration(
                    id=row[0],
                    session_id=row[1],
                    agent_type=AgentType(row[2]),
                    prompt=row[3],
                    files_changed=json.loads(row[4]),
                    error_message=row[5],
                    success=bool(row[6]),
                    tokens_used=row[7],
                    duration_seconds=row[8],
                    timestamp=row[9],
                    notes=row[10],
                )
            )
        return iterations

    def get_session_ids(self) -> list[str]:
        """Get all unique session IDs."""
        rows = self._conn.execute("SELECT DISTINCT session_id FROM iterations ORDER BY timestamp DESC").fetchall()
        return [r[0] for r in rows]

    def delete_session(self, session_id: str) -> int:
        """Delete all iterations for a session. Returns number deleted."""
        cursor = self._conn.execute("DELETE FROM iterations WHERE session_id = ?", (session_id,))
        self._conn.commit()
        return cursor.rowcount

    def clear_all(self) -> int:
        """Clear all iterations. Returns number deleted."""
        cursor = self._conn.execute("DELETE FROM iterations")
        self._conn.commit()
        return cursor.rowcount

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
