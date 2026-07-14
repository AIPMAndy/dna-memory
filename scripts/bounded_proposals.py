"""Extract explicit, bounded memory proposals without retaining transcripts."""

import json
import re
from pathlib import Path

from scripts.markdown_memory import SUPPORTED_TYPES
from scripts.policy import inspect_content


MARKER = re.compile(r"DNA_MEMORY_PROPOSAL\s*(\{.*?\})", re.DOTALL)
MAX_SUMMARY_CHARS = 800
DEFAULT_MAX_PROPOSALS = 3
DEFAULT_TAIL_BYTES = 64 * 1024


def extract_proposals(text, max_proposals=DEFAULT_MAX_PROPOSALS):
    """Return only valid JSON proposals explicitly emitted by an agent."""
    found = []
    for match in MARKER.finditer(str(text or "")):
        if len(found) >= max_proposals:
            break
        try:
            proposal = json.loads(match.group(1))
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(proposal, dict):
            continue
        summary = str(proposal.get("summary", "")).strip()
        if proposal.get("type") not in SUPPORTED_TYPES:
            continue
        if not summary or len(summary) > MAX_SUMMARY_CHARS:
            continue
        if not inspect_content(summary).allowed:
            continue
        confidence = proposal.get("confidence")
        if confidence is not None and confidence not in {"high", "medium", "low"}:
            continue
        importance = proposal.get("importance")
        if importance is not None and (
                isinstance(importance, bool)
                or not isinstance(importance, (int, float))
                or not 0.0 <= float(importance) <= 1.0):
            continue
        item = {"type": proposal["type"], "summary": summary}
        for key in ("confidence", "importance"):
            if key in proposal:
                item[key] = proposal[key]
        found.append(item)
    return found


def read_tail_proposals(path, max_bytes=DEFAULT_TAIL_BYTES,
                        max_proposals=DEFAULT_MAX_PROPOSALS):
    """Read at most the tail window; never return source text."""
    path = Path(path).expanduser()
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            data = handle.read(max_bytes)
    except OSError:
        return []
    return extract_proposals(data.decode("utf-8", errors="ignore"), max_proposals)
