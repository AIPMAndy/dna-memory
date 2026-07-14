#!/usr/bin/env python3
"""Bounded, idempotent queue of client event pointers."""

import sqlite3
from pathlib import Path

from scripts.policy import inspect_content


class CandidateEventQueue:
    def __init__(self, path, max_events=10000):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = int(max_events)
        self.connection = sqlite3.connect(str(path))
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS candidate_events (
                event_id TEXT PRIMARY KEY, client TEXT NOT NULL,
                event_type TEXT NOT NULL, session_id TEXT,
                project_path TEXT, source_ref TEXT, source_hash TEXT,
                excerpt TEXT, status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {
            row[1] for row in self.connection.execute(
                "PRAGMA table_info(candidate_events)"
            ).fetchall()
        }
        additions = {
            "memory_type": "TEXT", "confidence": "TEXT",
            "importance": "REAL", "processed_at": "TEXT",
            "memory_id": "TEXT", "error": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                self.connection.execute(
                    "ALTER TABLE candidate_events ADD COLUMN {} {}".format(name, definition)
                )
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS import_checkpoints (
                source_ref TEXT PRIMARY KEY, inode INTEGER, offset INTEGER NOT NULL DEFAULT 0,
                source_hash TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def enqueue(self, event):
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            if event.get("event_type") != "memory_proposal":
                pending = self.connection.execute(
                    "SELECT COUNT(*) FROM candidate_events WHERE status='pending' "
                    "AND event_type!='memory_proposal'"
                ).fetchone()[0]
                if pending >= self.max_events:
                    self.connection.rollback()
                    return False
            excerpt = event.get("excerpt")
            if excerpt and not inspect_content(str(excerpt)).allowed:
                excerpt = None
            cursor = self.connection.execute("""
                INSERT OR IGNORE INTO candidate_events
                (event_id, client, event_type, session_id, project_path, source_ref,
                 source_hash, excerpt, memory_type, confidence, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event["event_id"], event["client"], event["event_type"],
                  event.get("session_id"), event.get("project_path"), event.get("source_ref"),
                  event.get("source_hash"), excerpt, event.get("memory_type"),
                  event.get("confidence"), event.get("importance")))
            self.connection.commit()
            return cursor.rowcount == 1
        except Exception:
            self.connection.rollback()
            raise

    def get_checkpoint(self, source_ref):
        return self.connection.execute(
            "SELECT inode, offset, source_hash FROM import_checkpoints WHERE source_ref=?",
            (str(source_ref),),
        ).fetchone()

    def update_checkpoint(self, source_ref, inode, offset, source_hash):
        self.connection.execute("""
            INSERT INTO import_checkpoints (source_ref, inode, offset, source_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_ref) DO UPDATE SET
                inode=excluded.inode, offset=excluded.offset,
                source_hash=excluded.source_hash, updated_at=CURRENT_TIMESTAMP
        """, (str(source_ref), int(inode), int(offset), source_hash))
        self.connection.commit()
