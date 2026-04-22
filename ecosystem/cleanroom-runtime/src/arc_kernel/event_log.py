from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import List, Optional

from .schemas import Event, EventKind


class EventLog:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else None
        self._events: List[Event] = []
        self._conn: sqlite3.Connection | None = None
        if self.db_path is not None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute('PRAGMA journal_mode=WAL')
            self._conn.execute('PRAGMA synchronous=NORMAL')
            self._conn.execute('PRAGMA busy_timeout=5000')
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    idx INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    kind TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    parent_event_id TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()
            self._events = self._load_existing()

    def _load_existing(self) -> List[Event]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT event_id, kind, actor, payload, parent_event_id, created_at FROM events ORDER BY idx ASC"
        ).fetchall()
        events: List[Event] = []
        for event_id, kind, actor, payload, parent_event_id, created_at in rows:
            events.append(
                Event(
                    kind=EventKind(kind),
                    actor=actor,
                    payload=json.loads(payload),
                    parent_event_id=parent_event_id,
                    event_id=event_id,
                    created_at=created_at,
                )
            )
        return events

    def append(self, event: Event) -> Event:
        self._events.append(event)
        if self._conn is not None:
            self._conn.execute(
                "INSERT OR REPLACE INTO events (event_id, kind, actor, payload, parent_event_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.kind.value,
                    event.actor,
                    json.dumps(event.payload, sort_keys=True),
                    event.parent_event_id,
                    event.created_at,
                ),
            )
            self._conn.commit()
        return event

    def all(self) -> List[Event]:
        return list(self._events)

    def slice_until(self, event_id: str) -> List[Event]:
        collected: List[Event] = []
        for event in self._events:
            collected.append(event)
            if event.event_id == event_id:
                break
        return collected

    def find_by_event_id(self, event_id: str) -> Optional[Event]:
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def find_latest(self, kind: EventKind, field_name: str, value: str) -> Optional[Event]:
        for event in reversed(self._events):
            if event.kind == kind and event.payload.get(field_name) == value:
                return event
        return None


    def export_jsonl(self, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('w', encoding='utf-8') as fh:
            for event in self._events:
                fh.write(json.dumps(event.to_dict(), sort_keys=True) + '\n')
        return target

    def import_jsonl(self, input_path: str | Path) -> int:
        source = Path(input_path)
        imported = 0
        seen_ids = {event.event_id for event in self._events}
        with source.open('r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                event = Event.from_dict(raw)
                if event.event_id in seen_ids:
                    continue
                self.append(event)
                seen_ids.add(event.event_id)
                imported += 1
        return imported

    def checkpoint(self) -> None:
        if self._conn is None:
            return
        self._conn.commit()
        self._conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self._conn.commit()

    def vacuum(self) -> None:
        if self._conn is None:
            return
        self.checkpoint()
        self._conn.execute('VACUUM')
        self._conn.commit()

    def stats(self) -> dict:
        db_bytes = self.db_path.stat().st_size if self.db_path and self.db_path.exists() else 0
        wal_path = self.db_path.with_suffix(self.db_path.suffix + '-wal') if self.db_path else None
        wal_bytes = wal_path.stat().st_size if wal_path and wal_path.exists() else 0
        return {
            'event_count': len(self._events),
            'db_path': str(self.db_path) if self.db_path else None,
            'db_bytes': db_bytes,
            'wal_bytes': wal_bytes,
        }

    def backup_sqlite(self, output_path: str | Path) -> Path:
        if self.db_path is None:
            raise ValueError('SQLite backup requires a file-backed event log.')
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if self._conn is not None:
            self._conn.commit()
        shutil.copy2(self.db_path, target)
        wal_path = self.db_path.with_suffix(self.db_path.suffix + '-wal')
        if wal_path.exists():
            shutil.copy2(wal_path, target.with_suffix(target.suffix + '.wal'))
        return target

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
