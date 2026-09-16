from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import TypedDict, cast

from whisper_microfone.config.paths import history_db_path
from whisper_microfone.config.schemas import HistoryConfig

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id          INTEGER PRIMARY KEY,
    timestamp   TEXT    NOT NULL,
    language    TEXT    NOT NULL DEFAULT '',
    text        TEXT    NOT NULL DEFAULT '',
    duration_ms REAL    NOT NULL DEFAULT 0.0,
    latency_ms  REAL    NOT NULL DEFAULT 0.0
)
"""

_PRAGMA_WAL = "PRAGMA journal_mode=WAL"


class HistoryEntry(TypedDict):
    id: int
    timestamp: str
    language: str
    text: str
    duration_ms: float
    latency_ms: float


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class HistoryStore:
    def __init__(self, config: HistoryConfig) -> None:
        self._config = config
        self._db_path = history_db_path()
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_PRAGMA_WAL)
            conn.execute(_CREATE_TABLE)
            conn.commit()

    def _trim_to_max(self, conn: sqlite3.Connection) -> None:
        total = conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]
        excess = total - self._config.max_entries
        if excess > 0:
            conn.execute(
                """
                DELETE FROM transcriptions
                WHERE id IN (
                    SELECT id FROM transcriptions
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(
        self,
        text: str,
        duration_ms: float,
        latency_ms: float,
        language: str = "",
    ) -> None:
        if not self._config.enabled:
            return
        stored_text = text if self._config.store_text else ""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transcriptions (timestamp, language, text, duration_ms, latency_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (_utc_now(), language, stored_text, duration_ms, latency_ms),
            )
            self._trim_to_max(conn)
            conn.commit()

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        filter_lang: str = "",
        search: str = "",
    ) -> list[HistoryEntry]:
        clauses: list[str] = []
        params: list[str | int] = []

        if filter_lang:
            clauses.append("language = ?")
            params.append(filter_lang)

        if search:
            clauses.append("text LIKE ?")
            params.append(f"%{search}%")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.extend([limit, offset])

        query = f"""
            SELECT id, timestamp, language, text, duration_ms, latency_ms
            FROM transcriptions
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [cast(HistoryEntry, dict(row)) for row in rows]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM transcriptions")
            conn.commit()

    def auto_clean(self, days: int | None = None) -> None:
        effective_days = days if days is not None else self._config.auto_clean_after_days
        if effective_days <= 0:
            return
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM transcriptions
                WHERE datetime(timestamp) < datetime('now', ? || ' days')
                """,
                (f"-{effective_days}",),
            )
            conn.commit()

    def count(self) -> int:
        with self._connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()
        return int(result[0])


# ------------------------------------------------------------------
# Smoke test
# ------------------------------------------------------------------
if __name__ == "__main__":
    store = HistoryStore(HistoryConfig())

    store.add("teste de transcrição", 3000, 412, "pt")

    entries = store.list()
    print("list():", entries)

    total = store.count()
    print("count():", total)

    store.clear()
    assert store.count() == 0, "clear() deveria zerar o count"
    print("clear() ok — count() == 0")
