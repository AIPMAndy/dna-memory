import json

from scripts.candidate_events import CandidateEventQueue
from scripts.import_claudian_sessions import import_sessions


def test_claudian_import_is_metadata_only_and_idempotent(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    session = sessions / "conv-1.meta.json"
    session.write_text(json.dumps({
        "id": "conv-1", "providerId": "claude", "sessionId": "provider-1",
        "updatedAt": 1234, "title": "private title must not be copied",
        "usage": {"inputTokens": 999},
        "providerState": {"subagentData": {"x": {"toolOutput": "secret output"}}},
    }))
    queue = CandidateEventQueue(tmp_path / "memory.db")

    first = import_sessions([sessions], queue, project_path=tmp_path)
    second = import_sessions([sessions], queue, project_path=tmp_path)

    assert first == {"files": 1, "enqueued": 1, "skipped": 0}
    assert second == {"files": 1, "enqueued": 0, "skipped": 1}
    row = queue.connection.execute(
        "SELECT client,event_type,session_id,project_path,source_ref,excerpt FROM candidate_events"
    ).fetchone()
    assert tuple(row) == (
        "claudian", "session_updated", "conv-1", str(tmp_path), str(session.resolve()), None,
    )
    serialized = json.dumps(tuple(row))
    assert "private title" not in serialized
    assert "secret output" not in serialized
