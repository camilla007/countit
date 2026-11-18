from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .model import Bucket, EventClass

SCHEMA = """
CREATE TABLE IF NOT EXISTS minute_buckets (
    minute_utc TEXT PRIMARY KEY,
    printable INTEGER NOT NULL DEFAULT 0 CHECK (printable >= 0),
    corrections INTEGER NOT NULL DEFAULT 0 CHECK (corrections >= 0),
    navigation INTEGER NOT NULL DEFAULT 0 CHECK (navigation >= 0),
    modifiers INTEGER NOT NULL DEFAULT 0 CHECK (modifiers >= 0),
    other INTEGER NOT NULL DEFAULT 0 CHECK (other >= 0),
    active_seconds REAL NOT NULL DEFAULT 0 CHECK (active_seconds >= 0)
);
"""


class Store:
    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(database)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute(SCHEMA)
        self.conn.commit()

    @staticmethod
    def minute(timestamp: datetime) -> str:
        return timestamp.astimezone(UTC).replace(second=0, microsecond=0).isoformat()

    def add(self, event: EventClass, timestamp: datetime, active_seconds: float) -> None:
        column = {
            EventClass.PRINTABLE: "printable", EventClass.CORRECTION: "corrections",
            EventClass.NAVIGATION: "navigation", EventClass.MODIFIER: "modifiers", EventClass.OTHER: "other",
        }[event]
        minute = self.minute(timestamp)
        self.conn.execute(
            f"INSERT INTO minute_buckets(minute_utc, {column}, active_seconds) VALUES (?, 1, ?) "
            f"ON CONFLICT(minute_utc) DO UPDATE SET {column}={column}+1, active_seconds=active_seconds+excluded.active_seconds",
            (minute, active_seconds),
        )
        self.conn.commit()

    def buckets_since(self, since: datetime) -> list[Bucket]:
        rows = self.conn.execute(
            "SELECT minute_utc, printable, corrections, navigation, modifiers, other, active_seconds "
            "FROM minute_buckets WHERE minute_utc >= ? ORDER BY minute_utc", (since.astimezone(UTC).isoformat(),)
        ).fetchall()
        return [Bucket(*row) for row in rows]

    def purge_before(self, before: datetime) -> int:
        cursor = self.conn.execute("DELETE FROM minute_buckets WHERE minute_utc < ?", (before.astimezone(UTC).isoformat(),))
        self.conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self.conn.close()
