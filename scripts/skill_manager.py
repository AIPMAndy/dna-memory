#!/usr/bin/env python3
"""Non-destructive inventory and distribution for shared Agent Skills."""

import hashlib
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SkillFinding:
    name: str
    platform: str
    state: str
    path: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class SyncItem:
    name: str
    platform: str
    action: str
    source: str
    target: str

    def to_dict(self):
        return asdict(self)


def _entries(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return []
    return sorted(root.iterdir(), key=lambda path: path.name.lower())


def _digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((item for item in root.rglob("*") if item.is_file())):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _is_correct_link(target: Path, source: Path) -> bool:
    return target.is_symlink() and target.exists() and target.resolve() == source.resolve()


def inventory(shared_root: Path, platform_roots: Dict[str, Path], registry: dict) -> List[SkillFinding]:
    managed = registry.get("skills", {})
    findings = []
    for platform, root in sorted(platform_roots.items()):
        for target in _entries(root):
            name = target.name
            source = shared_root / name
            if target.is_symlink() and not target.exists():
                state = "broken_link"
            elif name not in managed:
                state = "platform"
            elif _is_correct_link(target, source):
                state = "shared"
            elif source.is_dir() and target.is_dir() and _digest(source) == _digest(target):
                state = "shadowed"
            else:
                state = "conflict"
            findings.append(SkillFinding(name, platform, state, str(target)))
    return findings


def build_sync_plan(shared_root: Path, platform_roots: Dict[str, Path], registry: dict) -> List[SyncItem]:
    plan = []
    for name, settings in sorted(registry.get("skills", {}).items()):
        source = shared_root / name
        for platform in settings.get("targets", []):
            root = platform_roots.get(platform)
            target = (root / name) if root else Path("<unconfigured>") / name
            if root is None:
                action = "unconfigured_platform"
            elif not source.is_dir() or not (source / "SKILL.md").is_file():
                action = "missing_source"
            elif _is_correct_link(target, source):
                action = "ok"
            elif target.is_symlink() or target.exists():
                action = "blocked_conflict"
            else:
                action = "create_link"
            plan.append(SyncItem(name, platform, action, str(source), str(target)))
    return plan


def apply_sync_plan(plan: List[SyncItem], apply: bool = False) -> int:
    if not apply:
        return 0
    changed = 0
    for item in plan:
        if item.action != "create_link":
            continue
        target = Path(item.target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(Path(item.source), target_is_directory=True)
        changed += 1
    return changed
