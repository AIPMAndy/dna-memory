#!/usr/bin/env python3
"""Privacy-bounded value metrics for the cross-client memory loop."""

import json
import sqlite3
from datetime import datetime
from urllib.parse import quote


CLIENT_FIELDS = (
    "candidate_events", "recall_attempts", "returned_memories",
    "useful", "misleading", "new_memories",
)


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


def _window_clause(column, days, now):
    if days is None:
        return "", ()
    return (
        " WHERE datetime({}) >= datetime(?, ?) "
        "AND datetime({}) <= datetime(?)".format(column, column),
        (now, "-{} days".format(days), now),
    )


def _metrics(connection, days, now):
    metrics = {
        "recall_attempts": 0, "recall_hits": 0, "hit_rate": 0.0,
        "returned_memories": 0, "useful": 0, "misleading": 0,
        "unfeedback": 0, "new_memories": 0,
    }
    if _table_exists(connection, "memory_recall_events"):
        clause, params = _window_clause("created_at", days, now)
        row = connection.execute(
            "SELECT COUNT(*), "
            "COALESCE(SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END), 0), "
            "COALESCE(SUM(result_count), 0) FROM memory_recall_events" + clause,
            params,
        ).fetchone()
        metrics["recall_attempts"] = row[0]
        metrics["recall_hits"] = row[1]
        metrics["returned_memories"] = row[2]
    if _table_exists(connection, "memory_feedback"):
        clause, params = _window_clause("created_at", days, now)
        rows = connection.execute(
            "SELECT outcome, COUNT(*) FROM memory_feedback" + clause +
            " GROUP BY outcome",
            params,
        ).fetchall()
        outcomes = {row[0]: row[1] for row in rows}
        metrics["useful"] = outcomes.get("useful", 0)
        metrics["misleading"] = outcomes.get("misleading", 0)
    if _table_exists(connection, "memory_index"):
        clause, params = _window_clause("created_at", days, now)
        prefix = " WHERE" if not clause else " AND"
        metrics["new_memories"] = connection.execute(
            "SELECT COUNT(*) FROM memory_index" + clause +
            prefix + " source_kind='markdown'",
            params,
        ).fetchone()[0]
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


def _storage(config):
    database_bytes = config.database_path.stat().st_size if config.database_path.is_file() else 0
    backup_bytes = 0
    if config.backup_dir.is_dir():
        backup_bytes = sum(
            path.stat().st_size for path in config.backup_dir.rglob("*") if path.is_file()
        )
    return {"database_bytes": database_bytes, "backup_bytes": backup_bytes}


def memory_value(config, now=None):
    now = now or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        "backlog": {"pending": 0, "oldest_pending_at": None},
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
            row = connection.execute(
                "SELECT COUNT(*), MIN(created_at) FROM candidate_events "
                "WHERE status='pending'"
            ).fetchone()
            payload["backlog"] = {
                "pending": row[0], "oldest_pending_at": row[1]
            }
        return payload
    finally:
        connection.close()


def _metrics_without_connection():
    return {
        "recall_attempts": 0, "recall_hits": 0, "hit_rate": 0.0,
        "returned_memories": 0, "useful": 0, "misleading": 0,
        "unfeedback": 0, "new_memories": 0,
    }
