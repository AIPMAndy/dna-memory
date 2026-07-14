#!/usr/bin/env python3
"""Safely migrate Claude Desktop from generic memory to DNA Memory MCP."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


GENERIC_COMMAND = "mcp-server-memory"


def _load_config(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid Claude Desktop config: {}".format(error))
    if not isinstance(payload, dict) or not isinstance(payload.get("mcpServers"), dict):
        raise ValueError("Claude Desktop config requires an mcpServers object")
    return payload


def _atomic_bytes(path, content, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent), delete=False
    )
    temp = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(str(temp), mode)
        os.replace(str(temp), str(path))
    finally:
        if temp.exists():
            temp.unlink()


def configure(
    config, python, server, profile, legacy_memory=None, backup_dir=None,
    apply=False, replace_custom=False, stamp=None,
):
    config = Path(config).expanduser()
    payload = _load_config(config)
    desired = {
        "command": str(Path(python).expanduser()),
        "args": [str(Path(server).expanduser())],
        "env": {"DNA_MEMORY_PROFILE": str(Path(profile).expanduser())},
    }
    current = payload["mcpServers"].get("dna-memory")
    if current == desired:
        return {"status": "already_configured", "changed": False}
    if current is None:
        action = "add"
    elif isinstance(current, dict) and current.get("command") == GENERIC_COMMAND:
        action = "replace"
    elif not replace_custom:
        raise ValueError("custom dna-memory server requires --replace-custom")
    else:
        action = "replace"
    if not apply:
        return {"status": "would_{}".format(action), "changed": False}

    stamp = stamp or datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = Path(backup_dir or config.parent / "dna-memory-backups").expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)
    config_backup = backup_dir / "{}.{}.bak".format(config.name, stamp)
    shutil.copy2(str(config), str(config_backup))
    result = {
        "status": "{}ed".format(action) if action == "add" else "replaced",
        "changed": True,
        "config_backup": str(config_backup),
        "legacy_backup": None,
    }
    if legacy_memory:
        legacy_memory = Path(legacy_memory).expanduser()
        if legacy_memory.is_file():
            legacy_backup = backup_dir / "{}.{}.bak".format(legacy_memory.name, stamp)
            shutil.copy2(str(legacy_memory), str(legacy_backup))
            result["legacy_backup"] = str(legacy_backup)

    payload["mcpServers"]["dna-memory"] = desired
    content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    _atomic_bytes(config, content, config.stat().st_mode & 0o777)
    return result


def rollback(config, backup):
    config = Path(config).expanduser()
    backup = Path(backup).expanduser()
    if not backup.is_file():
        raise ValueError("config backup not found: {}".format(backup))
    mode = config.stat().st_mode & 0o777 if config.exists() else backup.stat().st_mode & 0o777
    _atomic_bytes(config, backup.read_bytes(), mode)
    return {"status": "rolled_back", "changed": True, "backup": str(backup)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--python")
    parser.add_argument("--server")
    parser.add_argument("--profile")
    parser.add_argument("--legacy-memory")
    parser.add_argument("--backup-dir")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--replace-custom", action="store_true")
    parser.add_argument("--rollback")
    args = parser.parse_args(argv)
    try:
        if args.rollback:
            result = rollback(args.config, args.rollback)
        else:
            if not all((args.python, args.server, args.profile)):
                parser.error("--python, --server, and --profile are required")
            result = configure(
                args.config, args.python, args.server, args.profile,
                legacy_memory=args.legacy_memory, backup_dir=args.backup_dir,
                apply=args.apply, replace_custom=args.replace_custom,
            )
    except ValueError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
