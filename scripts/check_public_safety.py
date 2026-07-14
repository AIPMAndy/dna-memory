#!/usr/bin/env python3
"""Fail when the public source tree contains private deployment data."""

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv"}
SKIP_FILES = {Path(__file__).resolve()}

FORBIDDEN_LITERALS = (
    "/" + "Users/",
    "Andy" + "DATA",
    "com." + "andy",
    "andy" + "-profile",
    "andy" + "-memory-loop",
    "andy" + "-workflow",
    "andy" + "-zsxq",
    "andy" + "-mac",
    "-Users-" + "andy-",
)

SECRET_PATTERNS = (
    ("private key", re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?" + "PRIVATE KEY-----")),
    ("OpenAI-style token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "assigned secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|password)"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
)


def source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.resolve() in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def inspect_tree(root: Path):
    findings = []
    for path in source_files(root):
        try:
            raw = path.read_bytes()
            if b"\0" in raw:
                continue
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root)
        for literal in FORBIDDEN_LITERALS:
            if literal.lower() in text.lower() or literal.lower() in str(relative).lower():
                findings.append((str(relative), "private identifier", literal))
        for name, pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                findings.append((str(relative), name, "content redacted"))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    findings = inspect_tree(args.root.resolve())
    if findings:
        for path, kind, detail in findings:
            print("{}: {} ({})".format(path, kind, detail), file=sys.stderr)
        print("public safety check failed: {} finding(s)".format(len(findings)), file=sys.stderr)
        return 1
    print("public safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
