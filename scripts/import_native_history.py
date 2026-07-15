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


def import_paths(
    paths_by_client,
    queue,
    max_files=40,
    max_bytes=64 * 1024,
    min_age_seconds=120,
    reextract_days=None,
    now=None,
):
    reference_time = time.time() if now is None else float(now)
    if reextract_days is not None and int(reextract_days) <= 0:
        raise ValueError("reextract_days must be positive")
    cutoff = (
        reference_time - int(reextract_days) * 86400
        if reextract_days is not None else None
    )
    total = {
        "files": 0,
        "processed": 0,
        "enqueued": 0,
        "proposals": 0,
        "errors": 0,
        "proposal_types": {},
        "error_types": {},
    }
    for client, paths in source_files(paths_by_client).items():
        paths = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        pending = []
        for path in paths:
            stat = path.stat()
            if reference_time - stat.st_mtime < int(min_age_seconds):
                continue
            checkpoint = queue.get_checkpoint(
                "native-auto:{}:{}".format(client, path.expanduser().resolve())
            )
            force = cutoff is not None and stat.st_mtime >= cutoff
            if force or not checkpoint or checkpoint[0] != stat.st_ino or checkpoint[1] != stat.st_size:
                pending.append((path, force))
        for path, force in pending[:int(max_files)]:
            total["files"] += 1
            try:
                result = import_native_file(
                    path,
                    queue,
                    client=client,
                    max_bytes=max_bytes,
                    force=force,
                )
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
                total["errors"] += 1
                suffix = path.suffix.lower().lstrip(".") or "unknown"
                key = "{}:{}:{}".format(client, suffix, type(error).__name__)
                total["error_types"][key] = total["error_types"].get(key, 0) + 1
                continue
            total["processed"] += int(bool(result["processed"]))
            total["enqueued"] += result["enqueued"]
            total["proposals"] += result["proposals"]
            for memory_type, count in result.get("proposal_types", {}).items():
                total["proposal_types"][memory_type] = (
                    total["proposal_types"].get(memory_type, 0) + count
                )
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


def run_backtest(
    paths_by_client,
    database_path,
    days=7,
    max_files=40,
    max_bytes=64 * 1024,
    min_age_seconds=120,
    now=None,
):
    days = int(days)
    if days <= 0:
        raise ValueError("days must be positive")
    database_path = Path(database_path).expanduser().resolve()
    if database_path.exists() and database_path.stat().st_size > 0:
        raise ValueError("backtest database must be new or empty")
    reference_time = time.time() if now is None else float(now)
    cutoff = reference_time - days * 86400
    recent = {
        client: [
            path for path in paths
            if cutoff <= path.stat().st_mtime
            and reference_time - path.stat().st_mtime >= int(min_age_seconds)
        ]
        for client, paths in source_files(paths_by_client).items()
    }
    queue = CandidateEventQueue(database_path)
    try:
        result = import_paths(
            recent,
            queue,
            max_files=max_files,
            max_bytes=max_bytes,
            min_age_seconds=min_age_seconds,
            now=reference_time,
        )
    finally:
        queue.connection.close()
    return {"mode": "backtest", **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-files", type=int, default=int(os.getenv("DNA_MEMORY_MAX_FILES", "40")))
    parser.add_argument("--max-bytes", type=int, default=64 * 1024)
    parser.add_argument("--prune-obsolete", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--reextract-days", type=int)
    mode.add_argument("--backtest-days", type=int)
    parser.add_argument("--backtest-db", type=Path)
    args = parser.parse_args(argv)
    if args.reextract_days is not None and args.reextract_days <= 0:
        parser.error("--reextract-days must be positive")
    if args.backtest_days is not None and args.backtest_days <= 0:
        parser.error("--backtest-days must be positive")
    if bool(args.backtest_days) != bool(args.backtest_db):
        parser.error("--backtest-days and --backtest-db must be used together")
    config = load_config()
    paths = configured_paths(config)
    if args.backtest_days is not None:
        backtest_path = args.backtest_db.expanduser().resolve()
        if backtest_path == Path(config.database_path).expanduser().resolve():
            parser.error("--backtest-db must not be the production database")
        result = run_backtest(
            paths,
            backtest_path,
            days=args.backtest_days,
            max_files=args.max_files,
            max_bytes=args.max_bytes,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    queue = CandidateEventQueue(config.database_path, config.max_candidate_events)
    try:
        result = import_paths(
            paths,
            queue,
            args.max_files,
            args.max_bytes,
            reextract_days=args.reextract_days,
        )
        if args.prune_obsolete:
            result["pruned"] = prune_obsolete_sources(paths, queue)
    finally:
        queue.connection.close()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
