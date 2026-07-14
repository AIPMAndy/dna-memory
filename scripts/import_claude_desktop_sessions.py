#!/usr/bin/env python3
"""Capture bounded pointers from Claude Desktop and Cowork session metadata."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.candidate_events import CandidateEventQueue
from scripts.config import load_config


def import_sessions(paths, queue):
    result = {"files": 0, "enqueued": 0, "skipped": 0}
    for root in paths:
        root = Path(root).expanduser()
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("local_*.json")):
            result["files"] += 1
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            source_ref = str(path.resolve())
            checkpoint = queue.get_checkpoint(source_ref)
            if checkpoint and checkpoint[2] == digest:
                result["skipped"] += 1
                continue
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                result["skipped"] += 1
                continue
            session_id = str(
                payload.get("sessionId") or payload.get("cliSessionId") or ""
            ).strip()
            if not session_id:
                result["skipped"] += 1
                continue
            project_path = payload.get("cwd")
            if project_path is not None:
                project_path = str(project_path)
            identity = "{}|{}".format(source_ref, digest)
            event_id = "claude_desktop_{}".format(
                hashlib.sha256(identity.encode()).hexdigest()[:24]
            )
            if queue.enqueue({
                "event_id": event_id,
                "client": "claude-desktop",
                "event_type": "session_updated",
                "session_id": session_id,
                "project_path": project_path,
                "source_ref": source_ref,
                "source_hash": digest,
            }):
                result["enqueued"] += 1
            stat = path.stat()
            queue.update_checkpoint(source_ref, stat.st_ino, stat.st_size, digest)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    config = load_config()
    paths = args.paths or list(config.claude_desktop_session_dirs)
    queue = CandidateEventQueue(config.database_path, config.max_candidate_events)
    try:
        result = import_sessions(paths, queue)
    finally:
        queue.connection.close()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
