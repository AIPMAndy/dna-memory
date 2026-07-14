#!/usr/bin/env python3
"""CLI for cross-client Skill inventory, diagnosis, and safe sync."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from scripts.config import load_config
from scripts.skill_manager import apply_sync_plan, build_sync_plan, inventory


def _parser():
    parser = argparse.ArgumentParser(prog="dna skills")
    parser.add_argument("--profile", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "doctor", "sync"):
        command = sub.add_parser(name)
        command.add_argument("--json", action="store_true", dest="as_json")
        if name == "sync":
            command.add_argument("--apply", action="store_true")
    return parser


def _registry(path: Path) -> dict:
    if not path.is_file():
        return {"skills": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config(args.profile)
    registry = _registry(config.skill_registry)
    if args.command == "inventory":
        items = inventory(config.skill_root, config.platform_skill_roots, registry)
        _emit({"count": len(items), "items": [item.to_dict() for item in items]}, args.as_json)
        return 0
    if args.command == "doctor":
        items = inventory(config.skill_root, config.platform_skill_roots, registry)
        issues = [item for item in items if item.state in {"broken_link", "conflict"}]
        plan = build_sync_plan(config.skill_root, config.platform_skill_roots, registry)
        blocked = [item for item in plan if item.action not in {"ok", "create_link"}]
        _emit({
            "healthy": not issues and not blocked,
            "issues": [item.to_dict() for item in issues],
            "blocked": [item.to_dict() for item in blocked],
        }, args.as_json)
        return 0
    plan = build_sync_plan(config.skill_root, config.platform_skill_roots, registry)
    changed = apply_sync_plan(plan, apply=args.apply)
    _emit({
        "mode": "apply" if args.apply else "dry-run",
        "changed": changed,
        "items": [item.to_dict() for item in plan],
    }, args.as_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
