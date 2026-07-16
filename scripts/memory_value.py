#!/usr/bin/env python3
"""Privacy-bounded value metrics for the cross-client memory loop."""

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import quote


CLIENT_FIELDS = (
    "candidate_events", "recall_attempts", "returned_memories",
    "useful", "misleading", "new_memories",
)

OFFSET_WITHOUT_COLON = re.compile(r"([+-]\d{2})(\d{2})$")
PROVENANCE_EVENT_TYPES = frozenset((
    "session_updated", "session_meta", "turn_context",
))
LIFECYCLE_EVENT_TYPES = frozenset((
    "SessionStart", "Stop", "SessionEnd", "session_closed",
))


def _family(client):
    value = str(client or "unknown").strip().casefold()
    if value.startswith("codex"):
        return "codex"
    if value.startswith("claude") or value.startswith("claudian"):
        return "claude"
    if value.startswith("hermes"):
        return "hermes"
    return value or "unknown"


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.replace(".", "", 1).isdigit():
            return datetime.fromtimestamp(float(text), timezone.utc)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        text = OFFSET_WITHOUT_COLON.sub(r"\1:\2", text)
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _in_window(value, days, now):
    if days is None:
        return True
    created_at = _parse_timestamp(value)
    current = _parse_timestamp(now)
    if created_at is None or current is None:
        return False
    return current - timedelta(days=days) <= created_at <= current


def _windowed_rows(connection, table, columns, days, now):
    rows = connection.execute(
        "SELECT {} FROM {}".format(", ".join(columns), table)
    ).fetchall()
    return [row for row in rows if _in_window(row[-1], days, now)]


def _metrics(connection, days, now):
    metrics = {
        "recall_attempts": 0, "recall_hits": 0, "hit_rate": 0.0,
        "returned_memories": 0, "useful": 0, "misleading": 0,
        "unfeedback": 0, "new_memories": 0,
    }
    if _table_exists(connection, "memory_recall_events"):
        rows = _windowed_rows(
            connection, "memory_recall_events", ("result_count", "created_at"),
            days, now,
        )
        metrics["recall_attempts"] = len(rows)
        metrics["recall_hits"] = sum(1 for result_count, _ in rows if result_count > 0)
        metrics["returned_memories"] = sum(result_count for result_count, _ in rows)
    if _table_exists(connection, "memory_feedback"):
        rows = _windowed_rows(
            connection, "memory_feedback", ("outcome", "created_at"), days, now,
        )
        outcomes = {}
        for outcome, _ in rows:
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        metrics["useful"] = outcomes.get("useful", 0)
        metrics["misleading"] = outcomes.get("misleading", 0)
    if _table_exists(connection, "memory_index"):
        rows = _windowed_rows(
            connection, "memory_index", ("source_kind", "created_at"), days, now,
        )
        metrics["new_memories"] = sum(
            1 for source_kind, _ in rows if source_kind == "markdown"
        )
    attempts = metrics["recall_attempts"]
    metrics["hit_rate"] = metrics["recall_hits"] / attempts if attempts else 0.0
    metrics["unfeedback"] = max(
        0,
        metrics["returned_memories"] - metrics["useful"] - metrics["misleading"],
    )
    return metrics


def _client_metrics(connection):
    clients = {
        name: {field: 0 for field in CLIENT_FIELDS}
        for name in ("codex", "claude", "hermes")
    }

    def add(client, field, count):
        family = _family(client)
        clients.setdefault(family, {name: 0 for name in CLIENT_FIELDS})
        clients[family][field] += int(count or 0)

    if _table_exists(connection, "candidate_events"):
        for client, count in connection.execute(
            "SELECT client, COUNT(*) FROM candidate_events GROUP BY client"
        ):
            add(client, "candidate_events", count)
    if _table_exists(connection, "memory_recall_events"):
        for client, attempts, returned in connection.execute(
            "SELECT client, COUNT(*), COALESCE(SUM(result_count), 0) "
            "FROM memory_recall_events GROUP BY client"
        ):
            add(client, "recall_attempts", attempts)
            add(client, "returned_memories", returned)
    if _table_exists(connection, "memory_feedback"):
        for client, outcome, count in connection.execute(
            "SELECT client, outcome, COUNT(*) FROM memory_feedback "
            "GROUP BY client, outcome"
        ):
            if outcome in ("useful", "misleading"):
                add(client, outcome, count)
    if _table_exists(connection, "memory_index"):
        for raw_clients, in connection.execute(
            "SELECT clients FROM memory_index WHERE source_kind='markdown'"
        ):
            try:
                values = json.loads(raw_clients or "[]")
            except (TypeError, json.JSONDecodeError):
                values = []
            for client in set(values or ["unknown"]):
                add(client, "new_memories", 1)
    return clients


def _empty_backlog():
    return {
        "reviewable_proposals": 0,
        "provenance_events": 0,
        "lifecycle_events": 0,
        "other_pending": 0,
        "total_pending": 0,
        "pending": 0,
        "oldest_pending_at": None,
        "oldest_reviewable_at": None,
    }


def _backlog(connection):
    result = _empty_backlog()
    rows = connection.execute(
        "SELECT event_type, created_at FROM candidate_events WHERE status='pending'"
    ).fetchall()
    reviewable_times = []
    pending_times = []
    for event_type, created_at in rows:
        pending_times.append(created_at)
        if event_type == "memory_proposal":
            result["reviewable_proposals"] += 1
            reviewable_times.append(created_at)
        elif event_type in PROVENANCE_EVENT_TYPES:
            result["provenance_events"] += 1
        elif event_type in LIFECYCLE_EVENT_TYPES:
            result["lifecycle_events"] += 1
        else:
            result["other_pending"] += 1
    result["total_pending"] = len(rows)
    result["pending"] = len(rows)
    result["oldest_pending_at"] = min(pending_times) if pending_times else None
    result["oldest_reviewable_at"] = min(reviewable_times) if reviewable_times else None
    return result


def _storage(config):
    database_bytes = config.database_path.stat().st_size if config.database_path.is_file() else 0
    backup_bytes = 0
    if config.backup_dir.is_dir():
        backup_bytes = sum(
            path.stat().st_size for path in config.backup_dir.rglob("*") if path.is_file()
        )
    return {"database_bytes": database_bytes, "backup_bytes": backup_bytes}


def memory_value(config, now=None):
    now = now or datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "all_time": _metrics_without_connection(),
        "windows": {
            "7d": _metrics_without_connection(),
            "30d": _metrics_without_connection(),
        },
        "clients": {
            name: {field: 0 for field in CLIENT_FIELDS}
            for name in ("codex", "claude", "hermes")
        },
        "backlog": _empty_backlog(),
        "storage": _storage(config),
    }
    if not config.database_path.is_file():
        return payload
    uri = "file:{}?mode=ro".format(quote(str(config.database_path.resolve()), safe="/"))
    connection = sqlite3.connect(uri, uri=True)
    try:
        payload["all_time"] = _metrics(connection, None, now)
        payload["windows"]["7d"] = _metrics(connection, 7, now)
        payload["windows"]["30d"] = _metrics(connection, 30, now)
        payload["clients"] = _client_metrics(connection)
        if _table_exists(connection, "candidate_events"):
            payload["backlog"] = _backlog(connection)
        return payload
    finally:
        connection.close()


def _metrics_without_connection():
    return {
        "recall_attempts": 0, "recall_hits": 0, "hit_rate": 0.0,
        "returned_memories": 0, "useful": 0, "misleading": 0,
        "unfeedback": 0, "new_memories": 0,
    }
