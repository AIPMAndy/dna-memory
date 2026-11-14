#!/usr/bin/env python3
"""Read-only review of legacy pending memory proposals.

The old implementation automatically increased confidence and executed another
Python script to persist unverified text. This is unsafe for untrusted memory
content and is deliberately no longer supported. Use the validated
`dna memory remember` workflow after human review instead.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

DEFAULT_PENDING_FILE = Path.home() / ".local" / "state" / "dna-memory" / "pending.json"
MAX_PENDING_BYTES = 1024 * 1024


def review_pending(path: Path) -> int:
    """Report proposal counts without executing code or displaying memory text."""
    path = path.expanduser()
    if path.is_symlink():
        raise ValueError("Pending file must not be a symbolic link")
    if not path.exists():
        print("No legacy pending file; nothing to review.")
        return 0

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Pending file must be a regular file")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise ValueError("Pending file is not owned by the current user")
        if info.st_mode & 0o077:
            raise ValueError("Pending file permissions must be private (chmod 600)")
        with os.fdopen(fd, "rb", closefd=False) as file:
            raw = file.read(MAX_PENDING_BYTES + 1)
    finally:
        os.close(fd)

    if len(raw) > MAX_PENDING_BYTES:
        raise ValueError("Pending file exceeds the 1 MiB safety limit")
    proposals = json.loads(raw.decode("utf-8"))
    if not isinstance(proposals, list) or any(not isinstance(p, dict) for p in proposals):
        raise ValueError("Expected a list of pending memory objects")

    print(f"Pending proposals: {len(proposals)}")
    print("No proposals were promoted, written, or printed.")
    print("Review each proposal and use 'python3 dna.py memory remember --help' for verified writes.")
    return len(proposals)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pending-file", type=Path, default=DEFAULT_PENDING_FILE)
    args = parser.parse_args(argv)
    try:
        review_pending(args.pending_file)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Pending review refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
