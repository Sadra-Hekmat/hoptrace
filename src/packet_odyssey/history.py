from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .serialization import to_primitive


def default_history_path() -> Path:
    explicit = os.environ.get("PACKET_ODYSSEY_HISTORY")
    if explicit:
        return Path(explicit).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".local" / "share"
    return base / "packet-odyssey" / "history.db"


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_history_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    url TEXT NOT NULL,
                    scenario_id TEXT,
                    failure_type TEXT,
                    terminal_stage TEXT NOT NULL,
                    total_duration_ms INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save(self, run: Any) -> None:
        primitive = to_primitive(run)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                    id, created_at, status, url, scenario_id, failure_type,
                    terminal_stage, total_duration_ms, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    primitive["id"],
                    primitive["started_at"],
                    primitive["status"],
                    primitive["url"],
                    primitive.get("scenario_id"),
                    primitive.get("failure_type"),
                    primitive["terminal_stage"],
                    primitive["total_duration_ms"],
                    json.dumps(primitive, ensure_ascii=False),
                ),
            )

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, status, url, scenario_id, failure_type,
                       terminal_stage, total_duration_ms
                FROM runs ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM runs WHERE id = ?", (run_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def clear(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM runs")
        return cursor.rowcount
