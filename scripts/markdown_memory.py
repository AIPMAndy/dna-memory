#!/usr/bin/env python3
"""Adapter for explicitly managed Markdown memory pages."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

from scripts.policy import inspect_content


SUPPORTED_TYPES = {
    "preference", "decision", "fact", "insight", "workflow",
    "error_lesson", "project_state", "open_loop",
}


@dataclass(frozen=True)
class ReindexResult:
    scanned: int = 0
    indexed: int = 0
    skipped: int = 0
    removed: int = 0


def _parse(path: Path) -> Optional[Dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    try:
        raw, body = text[4:].split("\n---\n", 1)
        meta = yaml.safe_load(raw) or {}
    except (ValueError, yaml.YAMLError):
        return None
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if not meta.get("id") or meta.get("type") not in SUPPORTED_TYPES or "memory" not in tags:
        return None
    if meta.get("status", "active") not in {"active", "superseded", "archived", "rejected"}:
        return None
    supersedes = meta.get("supersedes", [])
    if supersedes is None:
        supersedes = []
    if not isinstance(supersedes, list) or not all(
        isinstance(item, str) and item.strip() for item in supersedes
    ):
        return None
    superseded_by = meta.get("superseded_by")
    if superseded_by is not None and (
        not isinstance(superseded_by, str) or not superseded_by.strip()
    ):
        return None
    policy = inspect_content(text)
    if not policy.allowed:
        return None
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
    if not paragraphs:
        return None
    digest = hashlib.sha256(text.encode()).hexdigest()
    return {
        "memory_id": str(meta["id"]),
        "markdown_path": str(path.resolve()),
        "type": meta["type"],
        "status": meta.get("status", "active"),
        "summary": " ".join(paragraphs[0].split()),
        "content_hash": digest,
        "source_hash": meta.get("source_hash"),
        "source_refs": meta.get("source_refs", []),
        "supersedes": supersedes,
        "superseded_by": superseded_by,
        "confidence": meta.get("confidence"),
        "importance": float(meta.get("importance", 0.5)),
        "sensitivity": meta.get("sensitivity", "normal"),
        "clients": meta.get("clients", []),
        "project_path": meta.get("project_path"),
        "session_id": meta.get("session_id"),
        "created_at": str(meta.get("created", "")),
        "updated_at": str(meta.get("updated", "")),
        "expires_at": str(meta.get("expires", "")),
    }


def reindex_markdown(root: Path, store) -> ReindexResult:
    root = Path(root)
    scanned = indexed = skipped = 0
    present = set()
    if root.exists():
        for path in root.rglob("*.md"):
            scanned += 1
            record = _parse(path)
            if record is None:
                skipped += 1
                continue
            present.add(record["memory_id"])
            if store.upsert_markdown(record):
                indexed += 1
    removed = store.remove_missing_markdown(present)
    store.commit()
    return ReindexResult(scanned, indexed, skipped, removed)
