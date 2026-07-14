#!/usr/bin/env python3
"""Bounded crystallization, retention, backup, and integrity operations."""

from datetime import datetime
from pathlib import Path
import sqlite3

from scripts.candidate_events import CandidateEventQueue
from scripts.markdown_memory import SUPPORTED_TYPES, reindex_markdown
from scripts.memory_service import MemoryService
from scripts.policy import inspect_content


class MemoryOperations:
    def __init__(self, config):
        self.config = config

    def daily(self, now=None):
        now = now or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        queue = CandidateEventQueue(self.config.database_path, self.config.max_candidate_events)
        result = {
            "crystallized": 0, "rejected": 0, "compacted": 0,
            "expired": 0, "deleted": 0,
        }
        try:
            proposals = queue.connection.execute("""
                SELECT event_id, client, session_id, project_path, source_ref,
                       source_hash, excerpt, memory_type, confidence, importance
                FROM candidate_events
                WHERE status='pending' AND event_type='memory_proposal'
                ORDER BY created_at, event_id
            """).fetchall()
            service = MemoryService(self.config)
            try:
                for row in proposals:
                    event_id, client, session_id, project_path, source_ref, source_hash, summary, mem_type, confidence, importance = row
                    error = self._proposal_error(mem_type, summary)
                    if error:
                        queue.connection.execute(
                            "UPDATE candidate_events SET status='rejected', processed_at=?, error=? WHERE event_id=?",
                            (now, error, event_id),
                        )
                        queue.connection.commit()
                        result["rejected"] += 1
                        continue
                    remembered = service.remember({
                        "type": mem_type, "summary": summary,
                        "source_hash": source_hash or "event:{}".format(event_id),
                        "confidence": confidence or "medium",
                        "importance": importance if importance is not None else 0.5,
                        "source_refs": [source_ref] if source_ref else [],
                        "clients": [client], "project_path": project_path,
                        "session_id": session_id,
                    })
                    queue.connection.execute(
                        "UPDATE candidate_events SET status='crystallized', processed_at=?, memory_id=?, error=NULL WHERE event_id=?",
                        (now, remembered["memory_id"], event_id),
                    )
                    queue.connection.commit()
                    result["crystallized"] += 1
            finally:
                service.store.close()

            cursor = queue.connection.execute("""
                UPDATE candidate_events AS event
                SET status='superseded', processed_at=?,
                    error='covered by codex session_meta pointer'
                WHERE event.status='pending' AND event.client='codex'
                  AND event.event_type NOT IN ('memory_proposal', 'session_meta')
                  AND event.session_id IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM candidate_events AS session
                      WHERE session.client='codex'
                        AND session.event_type='session_meta'
                        AND session.session_id=event.session_id
                  )
            """, (now,))
            result["compacted"] = cursor.rowcount
            cursor = queue.connection.execute("""
                UPDATE candidate_events
                SET status='expired', processed_at=?
                WHERE status='pending' AND event_type!='memory_proposal'
                  AND datetime(created_at) < datetime(?, '-30 days')
            """, (now, now))
            result["expired"] = cursor.rowcount
            cursor = queue.connection.execute("""
                DELETE FROM candidate_events
                WHERE status IN ('crystallized', 'rejected', 'superseded', 'expired')
                  AND datetime(COALESCE(processed_at, created_at)) < datetime(?, '-7 days')
            """, (now,))
            result["deleted"] = cursor.rowcount
            queue.connection.commit()
            return result
        finally:
            queue.connection.close()

    @staticmethod
    def _proposal_error(mem_type, summary):
        if mem_type not in SUPPORTED_TYPES:
            return "invalid memory type"
        if not summary or not str(summary).strip():
            return "missing safe summary"
        policy = inspect_content(str(summary))
        if not policy.allowed:
            return "sensitive summary rejected: {}".format(policy.reason)
        return None

    def weekly(self, now=None, backup_stamp=None):
        result = self.daily(now=now)
        stamp = backup_stamp or datetime.now().strftime("%Y%m%dT%H%M%S")
        self.config.backup_dir.mkdir(parents=True, exist_ok=True)
        target = self.config.backup_dir / "memory-{}.db".format(stamp)
        source = sqlite3.connect(str(self.config.database_path))
        backup = sqlite3.connect(str(target))
        try:
            source.backup(backup)
        finally:
            backup.close()
            source.close()
        backups = sorted(self.config.backup_dir.glob("memory-*.db"))
        for old in backups[:-max(1, self.config.backup_keep)]:
            old.unlink()
        connection = sqlite3.connect(str(self.config.database_path))
        try:
            connection.execute("VACUUM")
        finally:
            connection.close()
        result.update({"backup_path": str(target), "backups_kept": len(list(
            self.config.backup_dir.glob("memory-*.db")
        ))})
        return result

    def monthly(self, now=None, backup_stamp=None):
        result = self.weekly(now=now, backup_stamp=backup_stamp)
        connection = sqlite3.connect(str(self.config.database_path))
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
        service = MemoryService(self.config)
        try:
            rebuilt = reindex_markdown(self.config.knowledge_root, service.store)
        finally:
            service.store.close()
        result["integrity"] = integrity
        result["reindex"] = {
            "scanned": rebuilt.scanned, "indexed": rebuilt.indexed,
            "skipped": rebuilt.skipped, "removed": rebuilt.removed,
        }
        return result
