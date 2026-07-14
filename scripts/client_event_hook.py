#!/usr/bin/env python3
"""Nonblocking Claude lifecycle hook that stores metadata pointers only."""

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.candidate_events import CandidateEventQueue
from scripts.bounded_proposals import extract_proposals, read_tail_proposals
from scripts.config import load_config


def capture_payload(payload, database_path):
    session_id = str(payload.get("session_id", "")).strip()
    event_type = str(payload.get("hook_event_name", "")).strip()
    if not session_id or not event_type:
        return False
    source_ref = payload.get("transcript_path")
    source_size = -1
    if source_ref:
        try:
            source_size = Path(source_ref).stat().st_size
        except OSError:
            pass
    identity = "|".join((session_id, event_type, str(source_ref or ""), str(source_size)))
    digest = hashlib.sha256(identity.encode()).hexdigest()
    queue = CandidateEventQueue(database_path)
    try:
        enqueued = queue.enqueue({
            "event_id": "claude_{}".format(digest[:24]),
            "client": "claude",
            "event_type": event_type,
            "session_id": session_id,
            "project_path": payload.get("cwd"),
            "source_ref": source_ref,
            "source_hash": digest,
        })
        assistant_message = payload.get("last_assistant_message")
        if isinstance(assistant_message, str):
            proposals = extract_proposals(assistant_message)
            proposal_ref = source_ref or "hook:last_assistant_message"
        else:
            proposals = read_tail_proposals(source_ref) if source_ref else []
            proposal_ref = source_ref
        for index, proposal in enumerate(proposals):
            proposal_hash = hashlib.sha256(
                (digest + str(index) + proposal["summary"]).encode()
            ).hexdigest()
            enqueued = queue.enqueue({
                "event_id": "claude_proposal_{}".format(proposal_hash[:24]),
                "client": "claude",
                "event_type": "memory_proposal",
                "session_id": session_id,
                "project_path": payload.get("cwd"),
                "source_ref": "{}#proposal={}".format(proposal_ref, index),
                "source_hash": proposal_hash,
                "excerpt": proposal["summary"],
                "memory_type": proposal["type"],
                "confidence": proposal.get("confidence"),
                "importance": proposal.get("importance"),
            }) or enqueued
        return enqueued
    finally:
        queue.connection.close()


def main():
    try:
        payload = json.load(sys.stdin)
        capture_payload(payload, load_config().database_path)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
