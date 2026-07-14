#!/usr/bin/env python3
"""Incrementally import bounded pointers from append-only Codex rollouts."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.candidate_events import CandidateEventQueue
from scripts.bounded_proposals import (
    DEFAULT_MAX_PROPOSALS, DEFAULT_TAIL_BYTES, extract_proposals,
)
from scripts.config import load_config


SESSION_ID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def _fingerprint(path):
    with Path(path).open("rb") as handle:
        return hashlib.sha256(handle.readline(4096)).hexdigest()


def _event_type(record):
    return "session_meta" if record.get("type") == "session_meta" else None


def _assistant_text(payload):
    if payload.get("role") not in (None, "assistant"):
        return ""
    text = []
    for key in ("text", "output", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            text.append(value)
    content = payload.get("content")
    if isinstance(content, str):
        text.append(content)
    elif isinstance(content, list):
        text.extend(
            item.get("text", "") for item in content
            if isinstance(item, dict) and item.get("type") == "output_text"
            and isinstance(item.get("text"), str)
        )
    return "\n".join(text)


def _import_tail_proposals(path, queue, session_id=None, project_path=None):
    """Backfill explicit proposals once per changed transcript tail."""
    path = Path(path)
    scan_ref = "codex-proposals:{}".format(path)
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - DEFAULT_TAIL_BYTES))
            tail = handle.read(DEFAULT_TAIL_BYTES)
    except OSError:
        return 0
    digest = hashlib.sha256(tail).hexdigest()
    checkpoint = queue.get_checkpoint(scan_ref)
    if checkpoint and checkpoint[2] == digest:
        return 0
    enqueued = 0
    proposal_count = 0
    base_offset = max(0, size - len(tail))
    relative_offset = 0
    for raw in tail.splitlines(True):
        line_offset = base_offset + relative_offset
        relative_offset += len(raw)
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        payload = record.get("payload", {})
        if record.get("type") == "session_meta":
            session_id = payload.get("id") or payload.get("session_id") or session_id
            project_path = payload.get("cwd") or project_path
        if record.get("type") != "response_item":
            continue
        remaining = DEFAULT_MAX_PROPOSALS - proposal_count
        if remaining <= 0:
            break
        for index, proposal in enumerate(extract_proposals(
                _assistant_text(payload), max_proposals=remaining)):
            proposal_hash = hashlib.sha256(
                (str(path) + str(line_offset) + json.dumps(proposal, sort_keys=True, ensure_ascii=False)).encode()
            ).hexdigest()
            if queue.enqueue({
                "event_id": "codex_proposal_{}".format(proposal_hash[:24]),
                "client": "codex", "event_type": "memory_proposal",
                "session_id": session_id, "project_path": project_path,
                "source_ref": "{}#tail-byte={}#proposal={}".format(path, line_offset, index),
                "source_hash": proposal_hash, "excerpt": proposal["summary"],
                "memory_type": proposal["type"], "confidence": proposal.get("confidence"),
                "importance": proposal.get("importance"),
            }):
                enqueued += 1
            proposal_count += 1
    queue.update_checkpoint(scan_ref, path.stat().st_ino, size, digest)
    return enqueued


def import_rollout(path, queue):
    path = Path(path).resolve()
    stat = path.stat()
    fingerprint = _fingerprint(path)
    checkpoint = queue.get_checkpoint(str(path))
    offset = 0
    if checkpoint:
        old_inode, old_offset, old_hash = checkpoint
        if old_inode == stat.st_ino and old_offset <= stat.st_size and old_hash == fingerprint:
            offset = old_offset

    matches = SESSION_ID_PATTERN.findall(path.name)
    session_id = matches[-1] if matches else None
    project_path = None
    processed = enqueued = 0
    next_offset = offset
    with path.open("rb") as handle:
        handle.seek(offset)
        while True:
            line_offset = handle.tell()
            raw = handle.readline()
            if not raw:
                break
            if not raw.endswith(b"\n"):
                break
            next_offset = handle.tell()
            processed += 1
            try:
                record = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            payload = record.get("payload", {})
            if record.get("type") == "session_meta":
                session_id = payload.get("id") or payload.get("session_id") or session_id
                project_path = payload.get("cwd") or project_path
            elif record.get("type") == "turn_context":
                project_path = payload.get("cwd") or project_path
            event_type = _event_type(record)
            if not event_type:
                continue
            source_hash = hashlib.sha256(raw).hexdigest()
            event_id = hashlib.sha256(
                "{}|{}|{}|{}".format(path, stat.st_ino, line_offset, source_hash).encode()
            ).hexdigest()
            if queue.enqueue({
                "event_id": "codex_{}".format(event_id[:24]),
                "client": "codex",
                "event_type": event_type,
                "session_id": session_id,
                "project_path": project_path,
                "source_ref": "{}#byte={}".format(path, line_offset),
                "source_hash": source_hash,
            }):
                enqueued += 1
    queue.update_checkpoint(str(path), stat.st_ino, next_offset, fingerprint)
    enqueued += _import_tail_proposals(path, queue, session_id, project_path)
    return {"processed": processed, "enqueued": enqueued}


def _rollouts(paths):
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.is_file() and path.suffix == ".jsonl":
            yield path
        elif path.is_dir():
            yield from path.rglob("*.jsonl")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    paths = args.paths or ["~/.codex/sessions", "~/.codex/archived_sessions"]
    config = load_config()
    queue = CandidateEventQueue(config.database_path, config.max_candidate_events)
    total = {"files": 0, "processed": 0, "enqueued": 0}
    try:
        for path in _rollouts(paths):
            result = import_rollout(path, queue)
            total["files"] += 1
            total["processed"] += result["processed"]
            total["enqueued"] += result["enqueued"]
    finally:
        queue.connection.close()
    print(json.dumps(total, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
