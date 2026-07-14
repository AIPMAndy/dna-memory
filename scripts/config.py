#!/usr/bin/env python3
"""Portable configuration for the unified memory and skill tools."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


DEFAULTS = {
    "knowledge_root": "~/Documents/DNA-Memory-Vault",
    "database_path": "~/.local/share/dna-memory/memory.db",
    "managed_memory_dir": "Memory",
    "skill_root": "~/.agents/skills",
    "skill_registry": "~/.config/dna-memory/skills.json",
    "platform_skill_roots": {},
    "warning_bytes": 100 * 1024 * 1024,
    "hard_bytes": 250 * 1024 * 1024,
    "max_records": 10000,
    "max_candidate_events": 10000,
    "backup_dir": "~/.local/share/dna-memory/backups/managed",
    "backup_keep": 8,
    "claudian_session_dirs": [],
    "claude_desktop_session_dirs": [],
    "hermes_state_db": None,
}
DEFAULT_PROFILE = Path.home() / ".config" / "dna-memory" / "profile.json"


@dataclass(frozen=True)
class DNAConfig:
    knowledge_root: Path
    database_path: Path
    managed_memory_dir: str
    skill_root: Path
    skill_registry: Path
    platform_skill_roots: Dict[str, Path] = field(default_factory=dict)
    warning_bytes: int = DEFAULTS["warning_bytes"]
    hard_bytes: int = DEFAULTS["hard_bytes"]
    max_records: int = DEFAULTS["max_records"]
    max_candidate_events: int = DEFAULTS["max_candidate_events"]
    backup_dir: Path = Path(DEFAULTS["backup_dir"]).expanduser()
    backup_keep: int = DEFAULTS["backup_keep"]
    claudian_session_dirs: tuple = ()
    claude_desktop_session_dirs: tuple = ()
    hermes_state_db: Optional[Path] = None


def _path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def load_config(profile_path: Optional[Path] = None) -> DNAConfig:
    values = dict(DEFAULTS)
    selected = profile_path or os.getenv("DNA_MEMORY_PROFILE")
    if not selected and DEFAULT_PROFILE.is_file():
        selected = DEFAULT_PROFILE
    if selected:
        profile = Path(selected).expanduser()
        with profile.open(encoding="utf-8") as handle:
            values.update(json.load(handle))
    roots = {name: _path(path) for name, path in values.get("platform_skill_roots", {}).items()}
    return DNAConfig(
        knowledge_root=_path(values["knowledge_root"]),
        database_path=_path(values["database_path"]),
        managed_memory_dir=str(values["managed_memory_dir"]),
        skill_root=_path(values["skill_root"]),
        skill_registry=_path(values["skill_registry"]),
        platform_skill_roots=roots,
        warning_bytes=int(values["warning_bytes"]),
        hard_bytes=int(values["hard_bytes"]),
        max_records=int(values["max_records"]),
        max_candidate_events=int(values["max_candidate_events"]),
        backup_dir=_path(values["backup_dir"]),
        backup_keep=int(values["backup_keep"]),
        claudian_session_dirs=tuple(_path(path) for path in values.get("claudian_session_dirs", [])),
        claude_desktop_session_dirs=tuple(
            _path(path) for path in values.get("claude_desktop_session_dirs", [])
        ),
        hermes_state_db=_path(values["hermes_state_db"]) if values.get("hermes_state_db") else None,
    )
