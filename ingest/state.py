from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FileRecord:
    path: str
    content_hash: str
    size_bytes: int
    compressed_size: int
    mtime: float
    status: str
    artifact_id: str | None
    updated_at: str


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                content_hash TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                compressed_size INTEGER NOT NULL DEFAULT 0,
                mtime REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                artifact_id TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content_hash TEXT,
                detail TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def get_active_files(self) -> dict[str, FileRecord]:
        rows = self._conn.execute(
            "SELECT * FROM files WHERE status = 'active'"
        ).fetchall()
        return {row["path"]: self._row_to_record(row) for row in rows}

    def get(self, path: str) -> FileRecord | None:
        row = self._conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
        return self._row_to_record(row) if row else None

    def upsert(
        self,
        path: str,
        content_hash: str,
        size_bytes: int,
        compressed_size: int,
        mtime: float,
        artifact_id: str | None = None,
    ) -> None:
        now = _now()
        self._conn.execute(
            """
            INSERT INTO files (path, content_hash, size_bytes, compressed_size, mtime, status, artifact_id, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                content_hash = excluded.content_hash,
                size_bytes = excluded.size_bytes,
                compressed_size = excluded.compressed_size,
                mtime = excluded.mtime,
                status = 'active',
                artifact_id = COALESCE(excluded.artifact_id, files.artifact_id),
                updated_at = excluded.updated_at
            """,
            (path, content_hash, size_bytes, compressed_size, mtime, artifact_id, now),
        )
        self._conn.commit()

    def set_artifact_id(self, path: str, artifact_id: str | None) -> None:
        self._conn.execute(
            "UPDATE files SET artifact_id = ?, updated_at = ? WHERE path = ?",
            (artifact_id, _now(), path),
        )
        self._conn.commit()

    def mark_removed(self, path: str) -> None:
        self._conn.execute(
            "UPDATE files SET status = 'removed', updated_at = ? WHERE path = ?",
            (_now(), path),
        )
        self._conn.commit()

    def log_event(
        self,
        path: str,
        event_type: str,
        content_hash: str | None = None,
        detail: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO events (path, event_type, content_hash, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (path, event_type, content_hash, detail, _now()),
        )
        self._conn.commit()

    def list_files(self) -> list[FileRecord]:
        rows = self._conn.execute("SELECT * FROM files ORDER BY path").fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_events(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> FileRecord:
        return FileRecord(
            path=row["path"],
            content_hash=row["content_hash"],
            size_bytes=row["size_bytes"],
            compressed_size=row["compressed_size"],
            mtime=row["mtime"],
            status=row["status"],
            artifact_id=row["artifact_id"],
            updated_at=row["updated_at"],
        )
