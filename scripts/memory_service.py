#!/usr/bin/env python3
"""Business API for Markdown-backed long-term memory."""

import os
import time
import uuid
import hashlib
import json
import re
import shutil
from pathlib import Path

import yaml

from scripts.markdown_memory import SUPPORTED_TYPES, reindex_markdown
from scripts.candidate_events import CandidateEventQueue
from scripts.policy import inspect_content
from scripts.unified_memory import UnifiedMemoryStore


class MemoryValidationError(ValueError):
    pass


class MemoryService:
    QUERY_TERM_RE = re.compile(r"[^\W_]+", re.UNICODE)

    def __init__(self, config):
        self.config = config
        self.store = UnifiedMemoryStore(config.database_path)

    def remember(self, proposal):
        summary = str(proposal.get("summary", "")).strip()
        mem_type = proposal.get("type")
        if mem_type not in SUPPORTED_TYPES or not summary:
            raise MemoryValidationError("type and summary are required")
        policy = inspect_content(summary)
        if not policy.allowed:
            raise MemoryValidationError("sensitive content rejected: {}".format(policy.reason))
        source_hash = proposal.get("source_hash")
        if source_hash:
            row = self.store.connection.execute(
                "SELECT memory_id FROM memory_index WHERE source_hash=?", (source_hash,)
            ).fetchone()
            if row:
                return {"created": False, "memory_id": row[0], "superseded": []}
        supersedes = self._normalize_supersedes(proposal.get("supersedes"))
        root = self.config.knowledge_root / self.config.managed_memory_dir
        targets = self._load_active_targets(supersedes, root)
        memory_id = "mem_{}".format(uuid.uuid4().hex)
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        meta = {
            "id": memory_id, "type": mem_type, "status": "active",
            "confidence": proposal.get("confidence", "medium"),
            "importance": float(proposal.get("importance", 0.5)),
            "created": now, "updated": now,
            "clients": proposal.get("clients", []),
            "source_hash": source_hash,
            "source_refs": proposal.get("source_refs", []),
            "supersedes": supersedes,
            "tags": ["memory", mem_type],
            "project_path": proposal.get("project_path"),
            "session_id": proposal.get("session_id"),
        }
        root.mkdir(parents=True, exist_ok=True)
        path = root / "{}.md".format(memory_id)
        replacements = {}
        for target in targets:
            old_meta = dict(target["meta"])
            old_meta["status"] = "superseded"
            old_meta["superseded_by"] = memory_id
            old_meta["updated"] = now
            replacements[target["path"]] = self._render_memory(
                old_meta, target["body"]
            )
        replacements[path] = self._render_memory(meta, summary)
        self._install_memory_files(replacements)
        return {
            "created": True, "memory_id": memory_id, "path": str(path),
            "superseded": supersedes,
        }

    @staticmethod
    def _normalize_supersedes(value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise MemoryValidationError("supersedes must be a list of memory IDs")
        result = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise MemoryValidationError(
                    "supersedes must contain non-empty memory IDs"
                )
            memory_id = item.strip()
            if memory_id not in result:
                result.append(memory_id)
        return result

    def _load_active_targets(self, memory_ids, root):
        root = Path(root).resolve()
        targets = []
        for memory_id in memory_ids:
            row = self.store.connection.execute(
                "SELECT memory_id, markdown_path, status, source_kind "
                "FROM memory_index WHERE memory_id=?", (memory_id,)
            ).fetchone()
            if not row:
                raise MemoryValidationError(
                    "superseded memory not found: {}".format(memory_id)
                )
            if row["source_kind"] != "markdown":
                raise MemoryValidationError(
                    "superseded memory is not Markdown-managed: {}".format(memory_id)
                )
            if row["status"] != "active":
                raise MemoryValidationError(
                    "superseded memory is not active: {}".format(memory_id)
                )
            path = Path(row["markdown_path"] or "").resolve()
            try:
                path.relative_to(root)
            except ValueError:
                raise MemoryValidationError(
                    "superseded memory is outside managed root: {}".format(memory_id)
                )
            try:
                text = path.read_text(encoding="utf-8")
                raw, body = text[4:].split("\n---\n", 1)
                meta = yaml.safe_load(raw) or {}
            except (OSError, ValueError, yaml.YAMLError):
                raise MemoryValidationError(
                    "superseded memory Markdown is invalid: {}".format(memory_id)
                )
            if not text.startswith("---\n") or meta.get("id") != memory_id:
                raise MemoryValidationError(
                    "superseded memory Markdown ID mismatch: {}".format(memory_id)
                )
            targets.append({"path": path, "meta": meta, "body": body})
        return targets

    @staticmethod
    def _render_memory(meta, body):
        return "---\n{}---\n\n{}\n".format(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            str(body).strip("\n"),
        )

    def _install_memory_files(self, replacements):
        transaction_id = uuid.uuid4().hex
        staged = {}
        backups = {}
        installed = []
        try:
            for path, content in replacements.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(".{}.{}.tmp".format(path.name, transaction_id))
                temp.write_text(content, encoding="utf-8")
                staged[path] = temp
            for path in replacements:
                if path.exists():
                    backup = path.with_name(
                        ".{}.{}.bak".format(path.name, transaction_id)
                    )
                    shutil.copy2(str(path), str(backup))
                    backups[path] = backup
            for path, temp in staged.items():
                os.replace(str(temp), str(path))
                installed.append(path)
            reindex_markdown(self.config.knowledge_root, self.store)
        except Exception:
            rollback_error = None
            for path in reversed(installed):
                backup = backups.get(path)
                try:
                    if backup and backup.exists():
                        os.replace(str(backup), str(path))
                    elif path.exists():
                        path.unlink()
                except OSError as error:
                    rollback_error = rollback_error or error
            for path, backup in backups.items():
                if path not in installed and backup.exists():
                    backup.unlink()
            for temp in staged.values():
                if temp.exists():
                    temp.unlink()
            if rollback_error is None:
                reindex_markdown(self.config.knowledge_root, self.store)
            else:
                raise RuntimeError("memory file rollback failed") from rollback_error
            raise
        else:
            for backup in backups.values():
                if backup.exists():
                    backup.unlink()

    @classmethod
    def _query_terms(cls, query):
        terms = []
        seen = set()
        for match in cls.QUERY_TERM_RE.findall(str(query or "")):
            term = match.casefold()
            if term and term not in seen:
                terms.append(term)
                seen.add(term)
        return terms

    def recall(self, query, limit=20, client=None, session_id=None):
        limit = max(1, min(int(limit), 20))
        terms = self._query_terms(query)
        if not terms:
            raise MemoryValidationError("query is required")
        patterns = ["%{}%".format(term) for term in terms]
        hit_count = " + ".join(
            "CASE WHEN lower(m.summary) LIKE ? THEN 1 ELSE 0 END" for _ in terms
        )
        matches = " OR ".join("lower(m.summary) LIKE ?" for _ in terms)
        sql = """
            WITH feedback_scores AS (
                SELECT memory_id,
                       SUM(CASE outcome
                           WHEN 'useful' THEN 1
                           WHEN 'misleading' THEN -1
                           ELSE 0 END) AS feedback_score
                FROM memory_feedback
                GROUP BY memory_id
            ), ranked AS (
                SELECT m.memory_id, m.type, m.status, m.summary, m.importance,
                       m.confidence, m.markdown_path, m.source_refs, m.clients,
                       m.updated_at, ({hit_count}) AS hit_count,
                       COALESCE(f.feedback_score, 0) AS feedback_score,
                       CASE lower(COALESCE(m.confidence, ''))
                           WHEN 'high' THEN 3
                           WHEN 'medium' THEN 2
                           WHEN 'low' THEN 1
                           ELSE 0
                       END AS confidence_rank
                FROM memory_index m
                LEFT JOIN feedback_scores f ON f.memory_id=m.memory_id
                WHERE m.status='active' AND ({matches})
            )
            SELECT memory_id, type, status, summary, importance, confidence,
                   markdown_path, source_refs, clients
            FROM ranked
            ORDER BY hit_count DESC, feedback_score DESC, confidence_rank DESC,
                     importance DESC, updated_at DESC
            LIMIT ?
        """.format(hit_count=hit_count, matches=matches)
        rows = self.store.connection.execute(
            sql, tuple(patterns + patterns + [limit])
        ).fetchall()
        self.store.connection.execute(
            "INSERT INTO memory_recall_events "
            "(query_hash, client, session_id, result_count) VALUES (?, ?, ?, ?)",
            (
                hashlib.sha256(str(query).encode()).hexdigest(),
                client,
                session_id,
                len(rows),
            ),
        )
        if rows:
            self.store.connection.executemany(
                "UPDATE memory_index "
                "SET recall_count=recall_count+1, last_recalled_at=CURRENT_TIMESTAMP "
                "WHERE memory_id=?",
                ((row["memory_id"],) for row in rows),
            )
        self.store.connection.commit()
        return [self._decode_record(row) for row in rows]

    def get(self, memory_id):
        row = self.store.connection.execute(
            "SELECT * FROM memory_index WHERE memory_id=?", (memory_id,)
        ).fetchone()
        return self._decode_record(row) if row else None

    @staticmethod
    def _decode_record(row):
        record = dict(row)
        for field in ("source_refs", "clients", "supersedes"):
            value = record.get(field)
            if isinstance(value, str):
                try:
                    record[field] = json.loads(value)
                except json.JSONDecodeError:
                    record[field] = []
        return record

    def feedback(self, memory_id, outcome, note=None, client=None, session_id=None):
        if not self.get(memory_id):
            raise MemoryValidationError("memory not found")
        outcome = str(outcome).strip()
        if not outcome:
            raise MemoryValidationError("outcome is required")
        if note and not inspect_content(str(note)).allowed:
            raise MemoryValidationError("sensitive content rejected")
        self.store.connection.execute(
            "INSERT INTO memory_feedback "
            "(memory_id, outcome, note, client, session_id) VALUES (?, ?, ?, ?, ?)",
            (memory_id, outcome, note, client, session_id),
        )
        self.store.connection.commit()
        return {"recorded": True}

    def close_session(self, client, session_id, project_path=None, source_ref=None):
        if not str(client).strip() or not str(session_id).strip():
            raise MemoryValidationError("client and session_id are required")
        identity = "|".join((str(client), str(session_id), str(source_ref or "")))
        event_id = "close_{}".format(hashlib.sha256(identity.encode()).hexdigest()[:24])
        queue = CandidateEventQueue(self.config.database_path, self.config.max_candidate_events)
        queue.enqueue({
            "event_id": event_id,
            "client": str(client),
            "event_type": "session_closed",
            "session_id": str(session_id),
            "project_path": project_path,
            "source_ref": source_ref,
        })
        queue.connection.close()
        return {"event_id": event_id}

    def reindex(self):
        return reindex_markdown(self.config.knowledge_root, self.store)

    def status(self):
        return {"managed_records": self.store.count_managed(), "truth_root": str(self.config.knowledge_root)}
