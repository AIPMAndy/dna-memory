import json

from scripts.candidate_events import CandidateEventQueue
from scripts.import_claude_desktop_sessions import import_sessions


def test_claude_desktop_import_is_metadata_only_and_idempotent(tmp_path):
    sessions = tmp_path / "sessions/account/workspace"
    sessions.mkdir(parents=True)
    session = sessions / "local_desktop-session.json"
    session.write_text(json.dumps({
        "sessionId": "desktop-session",
        "cliSessionId": "cli-session",
        "cwd": "/tmp/project",
        "createdAt": "2026-07-10T12:00:00Z",
        "lastActivityAt": "2026-07-11T12:00:00Z",
        "title": "private title",
        "initialMessage": "private initial message",
        "systemPrompt": "private system prompt",
        "account": {"email": "private-user@example.invalid"},
        "toolConfiguration": {"secret": "private tool configuration"},
    }))
    (sessions / "spaces.json").write_text('{"initialMessage":"ignored"}')
    nested = sessions / "local_output/.claude/tasks"
    nested.mkdir(parents=True)
    (nested / "1.json").write_text('{"prompt":"ignored task"}')
    (sessions / "local_output/audit.jsonl").write_text("private audit content\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")

    first = import_sessions([tmp_path / "sessions"], queue)
    second = import_sessions([tmp_path / "sessions"], queue)

    assert first == {"files": 1, "enqueued": 1, "skipped": 0}
    assert second == {"files": 1, "enqueued": 0, "skipped": 1}
    row = queue.connection.execute(
        "SELECT client,event_type,session_id,project_path,source_ref,source_hash,excerpt "
        "FROM candidate_events"
    ).fetchone()
    assert tuple(row[:5]) == (
        "claude-desktop", "session_updated", "desktop-session", "/tmp/project",
        str(session.resolve()),
    )
    assert len(row[5]) == 64
    assert row[6] is None
    serialized = json.dumps(tuple(row))
    for private in (
        "private title", "private initial message", "private system prompt",
        "private-user@example.invalid", "private tool configuration",
        "private audit content", "ignored task",
    ):
        assert private not in serialized


def test_claude_desktop_import_uses_cli_session_id_and_skips_invalid_json(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    (root / "local_bad.json").write_text("not-json")
    valid = root / "local_cli.json"
    valid.write_text(json.dumps({"cliSessionId": "cli-only", "cwd": None}))
    queue = CandidateEventQueue(tmp_path / "memory.db")

    result = import_sessions([root], queue)

    assert result == {"files": 2, "enqueued": 1, "skipped": 1}
    row = queue.connection.execute(
        "SELECT session_id,project_path FROM candidate_events"
    ).fetchone()
    assert tuple(row) == ("cli-only", None)
