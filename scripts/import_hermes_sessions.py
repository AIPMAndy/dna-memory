#!/usr/bin/env python3
"""Capture bounded, incremental pointers from Hermes state.db."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.candidate_events import CandidateEventQueue
from scripts.bounded_proposals import DEFAULT_MAX_PROPOSALS, extract_proposals
from scripts.config import load_config


REQUIRED = {
    "sessions": {"id", "source", "cwd", "message_count"},
    "messages": {"id", "session_id"},
}


def _connect(path):
    uri = "file:{}?mode=ro".format(quote(str(path.resolve()), safe="/"))
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _validate_schema(connection):
    for table, required in REQUIRED.items():
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info({})".format(table)
            )
        }
        if not exists or not required.issubset(columns):
            raise ValueError("required Hermes schema missing: {}".format(table))


def import_sessions(path, queue):
    path = Path(path).expanduser().resolve()
    connection = _connect(path)
    try:
        _validate_schema(connection)
        rows = connection.execute("""
            SELECT s.id, s.source, s.cwd, s.message_count,
                   COALESCE(MAX(m.id), 0) AS max_message_id
            FROM sessions s
            LEFT JOIN messages m ON m.session_id=s.id
            GROUP BY s.id, s.source, s.cwd, s.message_count
            ORDER BY s.id
        """).fetchall()
        proposals = {}
        for row in rows:
            messages = connection.execute(
                "SELECT id, content FROM messages WHERE session_id=? AND role='assistant' "
                "AND content IS NOT NULL ORDER BY id DESC LIMIT 8", (row["id"],)
            ).fetchall()
            proposals[row["id"]] = [(message["id"], proposal)
                for message in messages
                for proposal in extract_proposals(message["content"])][
                    :DEFAULT_MAX_PROPOSALS
                ]
    finally:
        connection.close()

    result = {"sessions": len(rows), "enqueued": 0, "skipped": 0}
    stat = path.stat()
    for row in rows:
        session_id = str(row["id"])
        digest = hashlib.sha256(json.dumps({
            "id": session_id,
            "source": row["source"],
            "cwd": row["cwd"],
            "message_count": row["message_count"],
            "max_message_id": row["max_message_id"],
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        checkpoint_ref = "hermes:{}#{}".format(path, session_id)
        checkpoint = queue.get_checkpoint(checkpoint_ref)
        session_changed = not (
            checkpoint and checkpoint[1] == int(row["max_message_id"]) and checkpoint[2] == digest
        )
        if not session_changed:
            result["skipped"] += 1
        source_ref = "{}#session={}&max_message_id={}".format(
            path, session_id, row["max_message_id"]
        )
        event_id = "hermes_{}".format(
            hashlib.sha256((source_ref + "|" + digest).encode()).hexdigest()[:24]
        )
        if session_changed and queue.enqueue({
            "event_id": event_id,
            "client": "hermes",
            "event_type": "session_updated",
            "session_id": session_id,
            "project_path": row["cwd"],
            "source_ref": source_ref,
            "source_hash": digest,
        }):
            result["enqueued"] += 1
        for message_id, proposal in proposals.get(row["id"], []):
            proposal_hash = hashlib.sha256(
                (source_ref + str(message_id) + proposal["summary"]).encode()
            ).hexdigest()
            if queue.enqueue({
                "event_id": "hermes_proposal_{}".format(proposal_hash[:24]),
                "client": "hermes",
                "event_type": "memory_proposal",
                "session_id": session_id,
                "project_path": row["cwd"],
                "source_ref": "{}&message_id={}".format(source_ref, message_id),
                "source_hash": proposal_hash,
                "excerpt": proposal["summary"],
                "memory_type": proposal["type"],
                "confidence": proposal.get("confidence"),
                "importance": proposal.get("importance"),
            }):
                result["enqueued"] += 1
        queue.update_checkpoint(checkpoint_ref, stat.st_ino, row["max_message_id"], digest)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?")
    args = parser.parse_args(argv)
    config = load_config()
    path = args.path or config.hermes_state_db
    if not path:
        parser.error("Hermes state database is not configured")
    queue = CandidateEventQueue(config.database_path, config.max_candidate_events)
    try:
        result = import_sessions(path, queue)
    except (OSError, sqlite3.Error, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        queue.connection.close()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
