#!/usr/bin/env python3
"""CLI for rebuildable long-term memory index operations."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from scripts.config import load_config
from scripts.client_coverage import build_coverage_report
from scripts.markdown_memory import reindex_markdown
from scripts.memory_operations import MemoryOperations
from scripts.policy import capacity_status
from scripts.unified_memory import UnifiedMemoryStore
from scripts.memory_value import memory_value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dna memory")
    parser.add_argument("--profile", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "reindex", "coverage"):
        command = sub.add_parser(name)
        command.add_argument("--json", action="store_true", dest="as_json")
    maintain = sub.add_parser("maintain")
    maintain.add_argument("level", choices=("daily", "weekly", "monthly"))
    maintain.add_argument("--json", action="store_true", dest="as_json")
    maintain.add_argument("--now")
    maintain.add_argument("--backup-stamp")
    value = sub.add_parser("value")
    value.add_argument("--json", action="store_true", dest="as_json")
    value.add_argument("--now")
    return parser


def _emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        for key, value in payload.items():
            print("{}: {}".format(key, value))


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config(args.profile)
    if args.command == "coverage":
        _emit(build_coverage_report(config), args.as_json)
        return 0
    if args.command == "value":
        _emit(memory_value(config, now=args.now), args.as_json)
        return 0
    if args.command == "maintain":
        operation = getattr(MemoryOperations(config), args.level)
        kwargs = {"now": args.now}
        if args.level != "daily":
            kwargs["backup_stamp"] = args.backup_stamp
        _emit(operation(**kwargs), args.as_json)
        return 0
    preflight = capacity_status(config.database_path, config.warning_bytes, config.hard_bytes)
    if args.command == "reindex" and not preflight.writable:
        _emit({
            "error": "capacity_blocked",
            "size_bytes": preflight.size_bytes,
            "max_records": config.max_records,
        }, args.as_json)
        return 2
    store = UnifiedMemoryStore(config.database_path)
    try:
        record_count = store.connection.execute("SELECT COUNT(*) FROM memory_index").fetchone()[0]
        if args.command == "reindex":
            cap = capacity_status(config.database_path, config.warning_bytes, config.hard_bytes)
            if not cap.writable:
                _emit({
                    "error": "capacity_blocked",
                    "size_bytes": cap.size_bytes,
                    "record_count": record_count,
                    "max_records": config.max_records,
                }, args.as_json)
                return 2
            result = reindex_markdown(config.knowledge_root, store)
            _emit({
                "scanned": result.scanned, "indexed": result.indexed,
                "skipped": result.skipped, "removed": result.removed,
            }, args.as_json)
            return 0
        cap = capacity_status(config.database_path, config.warning_bytes, config.hard_bytes)
        legacy = store.connection.execute(
            "SELECT COUNT(*) FROM memory_index WHERE source_kind='legacy_cache'"
        ).fetchone()[0]
        payload = {
            "truth_root": str(config.knowledge_root),
            "truth_root_exists": config.knowledge_root.is_dir(),
            "database_path": str(config.database_path),
            "managed_records": store.count_managed(),
            "legacy_records": legacy,
            "capacity": {
                "state": "warning" if record_count >= config.max_records and cap.state == "ok" else cap.state,
                "size_bytes": cap.size_bytes,
                "writable": cap.writable,
                "record_count": record_count,
                "max_records": config.max_records,
            },
        }
        _emit(payload, args.as_json)
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
