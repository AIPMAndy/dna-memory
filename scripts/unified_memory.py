#!/usr/bin/env python3
"""Rebuildable SQLite index for Markdown-backed long-term memories."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Set


SCHEMA_VERSION = 5


class UnifiedMemoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.migrate()

    def migrate(self) -> None:
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memory_index (
                memory_id TEXT PRIMARY KEY,
                markdown_path TEXT,
                type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                summary TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                source_hash TEXT,
                source_refs TEXT NOT NULL DEFAULT '[]',
                supersedes TEXT NOT NULL DEFAULT '[]',
                superseded_by TEXT,
                confidence TEXT,
                importance REAL NOT NULL DEFAULT 0.5,
                sensitivity TEXT NOT NULL DEFAULT 'normal',
                clients TEXT NOT NULL DEFAULT '[]',
                project_path TEXT,
                session_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_recalled_at TEXT,
                expires_at TEXT,
                legacy_id INTEGER UNIQUE,
                source_kind TEXT NOT NULL DEFAULT 'markdown'
            );
            CREATE INDEX IF NOT EXISTS idx_memory_index_type ON memory_index(type);
            CREATE INDEX IF NOT EXISTS idx_memory_index_source ON memory_index(source_kind);
            CREATE TABLE IF NOT EXISTS memory_links (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL DEFAULT 'related',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_id, target_id, relation_type),
                FOREIGN KEY (source_id) REFERENCES memory_index(memory_id),
                FOREIGN KEY (target_id) REFERENCES memory_index(memory_id)
            );
            CREATE TABLE IF NOT EXISTS memory_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                note TEXT,
                client TEXT,
                session_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (memory_id) REFERENCES memory_index(memory_id)
            );
            CREATE INDEX IF NOT EXISTS idx_memory_feedback_memory
                ON memory_feedback(memory_id);
            CREATE TABLE IF NOT EXISTS memory_recall_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                client TEXT,
                session_id TEXT,
                result_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_memory_recall_events_created
                ON memory_recall_events(created_at);
        """)
        columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(memory_index)").fetchall()
        }
        if "source_refs" not in columns:
            self.connection.execute(
                "ALTER TABLE memory_index ADD COLUMN source_refs TEXT NOT NULL DEFAULT '[]'"
            )
        if "recall_count" not in columns:
            self.connection.execute(
                "ALTER TABLE memory_index "
                "ADD COLUMN recall_count INTEGER NOT NULL DEFAULT 0"
            )
        if "supersedes" not in columns:
            self.connection.execute(
                "ALTER TABLE memory_index "
                "ADD COLUMN supersedes TEXT NOT NULL DEFAULT '[]'"
            )
        if "superseded_by" not in columns:
            self.connection.execute(
                "ALTER TABLE memory_index ADD COLUMN superseded_by TEXT"
            )
        self._migrate_legacy()
        self.connection.execute(
            "INSERT OR IGNORE INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
        )
        self.connection.commit()

    def _migrate_legacy(self) -> None:
        exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory'"
        ).fetchone()
        if not exists:
            return
        for row in self.connection.execute(
            "SELECT id, content, type, weight, created, updated FROM memory"
        ).fetchall():
            digest = hashlib.sha256(row["content"].encode()).hexdigest()
            self.connection.execute("""
                INSERT OR IGNORE INTO memory_index (
                    memory_id, type, summary, content_hash, importance,
                    created_at, updated_at, legacy_id, source_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'legacy_cache')
            """, (
                "legacy-{}".format(row["id"]), row["type"], row["content"], digest,
                row["weight"], str(row["created"] or ""), str(row["updated"] or ""), row["id"],
            ))

    def upsert_markdown(self, record: Dict[str, object]) -> bool:
        existing = self.connection.execute(
            "SELECT content_hash FROM memory_index WHERE memory_id=?", (record["memory_id"],)
        ).fetchone()
        if existing and existing["content_hash"] == record["content_hash"]:
            return False
        self.connection.execute("""
            INSERT INTO memory_index (
                memory_id, markdown_path, type, status, summary, content_hash,
                source_hash, source_refs, supersedes, superseded_by,
                confidence, importance, sensitivity, clients,
                project_path, session_id, created_at, updated_at, expires_at, source_kind
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'markdown')
            ON CONFLICT(memory_id) DO UPDATE SET
                markdown_path=excluded.markdown_path, type=excluded.type,
                status=excluded.status, summary=excluded.summary,
                content_hash=excluded.content_hash, source_hash=excluded.source_hash,
                source_refs=excluded.source_refs,
                supersedes=excluded.supersedes, superseded_by=excluded.superseded_by,
                confidence=excluded.confidence, importance=excluded.importance,
                sensitivity=excluded.sensitivity, clients=excluded.clients,
                project_path=excluded.project_path, session_id=excluded.session_id,
                created_at=excluded.created_at, updated_at=excluded.updated_at,
                expires_at=excluded.expires_at, source_kind='markdown'
        """, (
            record["memory_id"], record["markdown_path"], record["type"], record["status"],
            record["summary"], record["content_hash"], record.get("source_hash"),
            json.dumps(record.get("source_refs", []), ensure_ascii=False),
            json.dumps(record.get("supersedes", []), ensure_ascii=False),
            record.get("superseded_by"),
            record.get("confidence"), record.get("importance", 0.5),
            record.get("sensitivity", "normal"), json.dumps(record.get("clients", []), ensure_ascii=False),
            record.get("project_path"), record.get("session_id"), record.get("created_at"),
            record.get("updated_at"), record.get("expires_at"),
        ))
        return True

    def remove_missing_markdown(self, present_ids: Set[str]) -> int:
        rows = self.connection.execute(
            "SELECT memory_id FROM memory_index WHERE source_kind='markdown'"
        ).fetchall()
        missing = [row["memory_id"] for row in rows if row["memory_id"] not in present_ids]
        if missing:
            self.connection.executemany(
                "DELETE FROM memory_index WHERE memory_id=?", ((item,) for item in missing)
            )
        return len(missing)

    def count_managed(self) -> int:
        return self.connection.execute(
            "SELECT COUNT(*) FROM memory_index WHERE source_kind='markdown'"
        ).fetchone()[0]

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()
