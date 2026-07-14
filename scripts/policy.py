#!/usr/bin/env python3
"""Deterministic storage safety and capacity checks."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class CapacityStatus:
    state: str
    size_bytes: int
    writable: bool


RULES = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("api_token", re.compile(r"\b(?:sk|ghp|xox[baprs])-[A-Za-z0-9_-]{20,}\b")),
    ("password", re.compile(r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*\S+")),
)


def inspect_content(content: str) -> PolicyResult:
    if len(content) >= 5000 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", content):
        return PolicyResult(False, "large_encoded_block")
    for name, pattern in RULES:
        if pattern.search(content):
            return PolicyResult(False, name)
    return PolicyResult(True)


def capacity_status(path: Path, warning_bytes: int, hard_bytes: int) -> CapacityStatus:
    size = path.stat().st_size if path.exists() else 0
    if size >= hard_bytes:
        return CapacityStatus("blocked", size, False)
    if size >= warning_bytes:
        return CapacityStatus("warning", size, True)
    return CapacityStatus("ok", size, True)
