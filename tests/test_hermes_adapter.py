import hashlib
import json
import os
import sqlite3

import pytest

from scripts.candidate_events import CandidateEventQueue
from scripts.import_hermes_sessions import import_sessions


def source_db(path):
    connection = sqlite3.connect(str(path))
    connection.executescript("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, started_at REAL NOT NULL,
            ended_at REAL, message_count INTEGER DEFAULT 0, cwd TEXT
        );
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT, tool_calls TEXT, timestamp REAL NOT NULL
        );
    """)
    connection.execute(
        "INSERT INTO sessions VALUES ('s1', 'desktop', 1, NULL, 2, '/tmp/hermes')"
    )
    connection.executemany(
        "INSERT INTO messages(session_id,role,content,tool_calls,timestamp) "
        "VALUES ('s1', ?, ?, ?, ?)",
        [("user", "private message one", "private tool one", 1),
         ("assistant", "private message two", "private tool two", 2)],
    )
    connection.commit()
    connection.close()


def test_hermes_import_is_read_only_incremental_and_idempotent(tmp_path):
    source = tmp_path / "state.db"
    source_db(source)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    queue = CandidateEventQueue(tmp_path / "memory.db")

    first = import_sessions(source, queue)
    second = import_sessions(source, queue)

    assert first == {"sessions": 1, "enqueued": 1, "skipped": 0}
    assert second == {"sessions": 1, "enqueued": 0, "skipped": 1}
    row = queue.connection.execute(
        "SELECT client,event_type,session_id,project_path,source_ref,excerpt "
        "FROM candidate_events"
    ).fetchone()
    assert tuple(row) == (
        "hermes", "session_updated", "s1", "/tmp/hermes",
        str(source.resolve()) + "#session=s1&max_message_id=2", None,
    )
    serialized = json.dumps(tuple(row))
    assert "private message" not in serialized
    assert "private tool" not in serialized
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original

    connection = sqlite3.connect(str(source))
    connection.execute(
        "INSERT INTO messages(session_id,role,content,tool_calls,timestamp) "
        "VALUES ('s1', 'user', 'private message three', 'private tool three', 3)"
    )
    connection.commit()
    connection.close()

    third = import_sessions(source, queue)
    assert third == {"sessions": 1, "enqueued": 1, "skipped": 0}
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events"
    ).fetchone()[0] == 2
    assert queue.connection.execute(
        "SELECT MAX(source_ref) FROM candidate_events"
    ).fetchone()[0].endswith("max_message_id=3")


def test_hermes_import_rejects_incompatible_schema_without_checkpoint(tmp_path):
    source = tmp_path / "bad.db"
    connection = sqlite3.connect(str(source))
    connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
    connection.commit()
    connection.close()
    queue = CandidateEventQueue(tmp_path / "memory.db")

    with pytest.raises(ValueError, match="required Hermes schema"):
        import_sessions(source, queue)

    assert queue.connection.execute(
        "SELECT COUNT(*) FROM import_checkpoints"
    ).fetchone()[0] == 0


def test_hermes_imports_bounded_assistant_proposal_only(tmp_path):
    source = tmp_path / "state.db"
    source_db(source)
    connection = sqlite3.connect(str(source))
    connection.execute(
        "INSERT INTO messages(session_id,role,content,tool_calls,timestamp) VALUES (?, ?, ?, ?, ?)",
        ("s1", "assistant", "DNA_MEMORY_PROPOSAL {\"type\":\"decision\",\"summary\":\"Hermes 只读接入\"}", None, 3),
    )
    connection.commit()
    connection.close()
    queue = CandidateEventQueue(tmp_path / "memory.db")

    assert import_sessions(source, queue)["enqueued"] == 2
    row = queue.connection.execute(
        "SELECT event_type,memory_type,excerpt FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchone()
    assert tuple(row) == ("memory_proposal", "decision", "Hermes 只读接入")


def test_hermes_backfills_proposal_when_legacy_checkpoint_is_current(tmp_path):
    source = tmp_path / "state.db"
    source_db(source)
    connection = sqlite3.connect(str(source))
    connection.execute(
        "UPDATE messages SET content=? WHERE id=2",
        ("DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"旧 Hermes 会话\"}",),
    )
    connection.commit()
    connection.close()
    queue = CandidateEventQueue(tmp_path / "memory.db")

    assert import_sessions(source, queue)["enqueued"] == 2
    queue.connection.execute("DELETE FROM candidate_events WHERE event_type='memory_proposal'")
    queue.connection.commit()

    assert import_sessions(source, queue)["enqueued"] == 1
    assert import_sessions(source, queue)["enqueued"] == 0


def test_hermes_caps_proposals_across_recent_messages(tmp_path):
    source = tmp_path / "state.db"
    source_db(source)
    connection = sqlite3.connect(str(source))
    for index in range(4):
        connection.execute(
            "INSERT INTO messages(session_id,role,content,tool_calls,timestamp) VALUES (?, ?, ?, ?, ?)",
            ("s1", "assistant", "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"结论%s\"}" % index, None, 3 + index),
        )
    connection.commit()
    connection.close()
    queue = CandidateEventQueue(tmp_path / "memory.db")

    import_sessions(source, queue)
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchone()[0] == 3
