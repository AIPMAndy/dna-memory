from scripts.candidate_events import CandidateEventQueue


def test_candidate_events_are_idempotent_and_secret_safe(tmp_path):
    queue = CandidateEventQueue(tmp_path / "events.db")
    event = {"event_id": "e1", "client": "claude", "event_type": "Stop",
             "session_id": "s1", "source_ref": "/tmp/session.jsonl",
             "excerpt": "password=secret123"}
    assert queue.enqueue(event) is True
    assert queue.enqueue(event) is False
    row = queue.connection.execute(
        "SELECT excerpt, source_ref FROM candidate_events WHERE event_id='e1'"
    ).fetchone()
    assert row[0] is None
    assert row[1] == "/tmp/session.jsonl"


def test_candidate_events_apply_a_bound_without_blocking_proposals(tmp_path):
    queue = CandidateEventQueue(tmp_path / "bounded.db", max_events=2)
    assert queue.enqueue({"event_id": "e1", "client": "codex", "event_type": "task_complete"}) is True
    assert queue.enqueue({"event_id": "e2", "client": "codex", "event_type": "task_complete"}) is True
    assert queue.enqueue({"event_id": "e3", "client": "codex", "event_type": "task_complete"}) is False
    assert queue.enqueue({
        "event_id": "proposal-1", "client": "codex", "event_type": "memory_proposal",
        "memory_type": "fact", "excerpt": "bounded proposal",
    }) is True
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events"
    ).fetchone()[0] == 3
