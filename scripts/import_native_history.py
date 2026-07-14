#!/usr/bin/env python3
"""Bounded automatic importer for Codex, Claude, Cowork and Hermes history."""

import argparse
from dataclasses import dataclass
from fnmatch import fnmatch
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.candidate_events import CandidateEventQueue
from scripts.config import load_config
from scripts.native_auto_extract import import_native_file


@dataclass(frozen=True)
class SourceSpec:
    roots: tuple
    patterns: tuple
    prefer_jsonl_mirror: bool = False


def _has_jsonl_mirror(path):
    if not path.name.startswith("session_") or path.suffix != ".json":
        return False
    return path.with_name(path.name[len("session_"):-len(".json")] + ".jsonl").is_file()


def _files(spec):
    for raw in spec.roots:
        path = Path(raw).expanduser()
        if path.is_file() and any(fnmatch(path.name, pattern) for pattern in spec.patterns):
            yield path
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if not candidate.is_file():
                    continue
                if not any(fnmatch(candidate.name, pattern) for pattern in spec.patterns):
                    continue
                if spec.prefer_jsonl_mirror and _has_jsonl_mirror(candidate):
                    continue
                yield candidate


def _source_spec(client, value):
    if isinstance(value, SourceSpec):
        return value
    patterns = ("*.jsonl",) if client == "claude-desktop" else ("*.json", "*.jsonl")
    return SourceSpec(tuple(value), patterns)


def source_files(paths_by_client):
    return {
        client: sorted(set(_files(_source_spec(client, value))))
        for client, value in paths_by_client.items()
    }


def _matches_spec(path, spec):
    path = Path(path)
    if not any(fnmatch(path.name, pattern) for pattern in spec.patterns):
        return False
    if spec.prefer_jsonl_mirror and _has_jsonl_mirror(path):
        return False
    return True


def prune_obsolete_sources(paths_by_client, queue):
    specs = {
        client: _source_spec(client, value)
        for client, value in paths_by_client.items()
    }
    rows = queue.connection.execute(
        "SELECT source_ref FROM import_checkpoints WHERE source_ref LIKE 'native-auto:%'"
    ).fetchall()
    obsolete = []
    for row in rows:
        checkpoint_ref = row[0]
        try:
            _, client, raw_path = checkpoint_ref.split(":", 2)
        except ValueError:
            continue
        spec = specs.get(client)
        if spec and not _matches_spec(raw_path, spec):
            obsolete.append((checkpoint_ref, client, raw_path))
    events = 0
    for checkpoint_ref, client, raw_path in obsolete:
        cursor = queue.connection.execute(
            "DELETE FROM candidate_events WHERE client=? AND event_id LIKE 'auto_%' "
            "AND (source_ref=? OR source_ref LIKE ?)",
            (client, raw_path, raw_path + "#%"),
        )
        events += cursor.rowcount
        queue.connection.execute(
            "DELETE FROM import_checkpoints WHERE source_ref=?", (checkpoint_ref,)
        )
    queue.connection.commit()
    return {"checkpoints": len(obsolete), "events": events}


def import_paths(paths_by_client, queue, max_files=40, max_bytes=64 * 1024, min_age_seconds=120):
    total = {"files": 0, "processed": 0, "enqueued": 0, "proposals": 0}
    for client, paths in source_files(paths_by_client).items():
        paths = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        pending = []
        for path in paths:
            stat = path.stat()
            if time.time() - stat.st_mtime < int(min_age_seconds):
                continue
            checkpoint = queue.get_checkpoint(
                "native-auto:{}:{}".format(client, path.expanduser().resolve())
            )
            if not checkpoint or checkpoint[0] != stat.st_ino or checkpoint[1] != stat.st_size:
                pending.append(path)
        for path in pending[:int(max_files)]:
            try:
                result = import_native_file(path, queue, client=client, max_bytes=max_bytes)
            except (OSError, ValueError):
                continue
            total["files"] += 1
            total["processed"] += int(bool(result["processed"]))
            total["enqueued"] += result["enqueued"]
            total["proposals"] += result["proposals"]
    return total


def configured_paths(config):
    return {
        "codex": SourceSpec(
            ("~/.codex/sessions", "~/.codex/archived_sessions"), ("*.jsonl",)
        ),
        "claude-code": SourceSpec(("~/.claude/projects",), ("*.jsonl",)),
        "claude-desktop": SourceSpec(
            tuple(config.claude_desktop_session_dirs), ("audit.jsonl",)
        ),
        "hermes": SourceSpec(
            ("~/.hermes/sessions",), ("*.jsonl", "session_*.json"),
            prefer_jsonl_mirror=True,
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-files", type=int, default=int(os.getenv("DNA_MEMORY_MAX_FILES", "40")))
    parser.add_argument("--max-bytes", type=int, default=64 * 1024)
    parser.add_argument("--prune-obsolete", action="store_true")
    args = parser.parse_args(argv)
    config = load_config()
    queue = CandidateEventQueue(config.database_path, config.max_candidate_events)
    try:
        paths = configured_paths(config)
        result = import_paths(paths, queue, args.max_files, args.max_bytes)
        if args.prune_obsolete:
            result["pruned"] = prune_obsolete_sources(paths, queue)
    finally:
        queue.connection.close()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
