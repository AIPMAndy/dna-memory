import json
from pathlib import Path
import subprocess
import sys

from scripts.candidate_events import CandidateEventQueue


def test_claude_hook_keeps_only_lifecycle_metadata(tmp_path):
    from scripts.client_event_hook import capture_payload

    database = tmp_path / "memory.db"
    payload = {
        "session_id": "claude-session",
        "cwd": "/tmp/project",
        "hook_event_name": "Stop",
        "transcript_path": "/tmp/transcript.jsonl",
        "prompt": "private full prompt must not be copied",
        "tool_output": "large output must not be copied",
    }

    assert capture_payload(payload, database) is True
    queue = CandidateEventQueue(database)
    row = queue.connection.execute(
        "SELECT client, event_type, session_id, project_path, source_ref, excerpt "
        "FROM candidate_events"
    ).fetchone()
    assert tuple(row) == (
        "claude", "Stop", "claude-session", "/tmp/project",
        "/tmp/transcript.jsonl", None,
    )


def test_claude_hook_never_blocks_client_on_invalid_input(tmp_path):
    script = Path(__file__).parents[1] / "scripts/client_event_hook.py"
    result = subprocess.run(
        [sys.executable, str(script)], input="not-json", cwd=str(tmp_path),
        text=True, capture_output=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_claude_hook_reads_bounded_tail_for_explicit_proposal(tmp_path):
    from scripts.client_event_hook import capture_payload

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "private old content\n"
        "DNA_MEMORY_PROPOSAL {\"type\":\"workflow\",\"summary\":\"只保存验证后的结论\"}\n"
    )
    database = tmp_path / "memory.db"

    assert capture_payload({
        "session_id": "claude-session",
        "cwd": "/tmp/project",
        "hook_event_name": "Stop",
        "transcript_path": str(transcript),
    }, database) is True
    row = CandidateEventQueue(database).connection.execute(
        "SELECT event_type,memory_type,excerpt FROM candidate_events "
        "WHERE event_type='memory_proposal'"
    ).fetchone()
    assert tuple(row) == ("memory_proposal", "workflow", "只保存验证后的结论")


def test_claude_hook_prefers_last_assistant_message_and_ignores_prompt(tmp_path):
    from scripts.client_event_hook import capture_payload

    database = tmp_path / "memory.db"
    assert capture_payload({
        "session_id": "claude-session",
        "hook_event_name": "Stop",
        "prompt": "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"用户注入\"}",
        "last_assistant_message": "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"Claude 结论\"}",
    }, database) is True

    rows = CandidateEventQueue(database).connection.execute(
        "SELECT excerpt FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchall()
    assert [row[0] for row in rows] == ["Claude 结论"]


def test_codex_importer_reads_only_appended_bytes_and_checkpoints(tmp_path):
    from scripts.import_codex_rollouts import import_rollout

    rollout = tmp_path / "rollout-2026-01-01T00-00-00-session-123.jsonl"
    first_records = [
        {"type": "session_meta", "payload": {
            "id": "session-123", "cwd": "/tmp/project",
            "base_instructions": "must not be copied",
        }},
        {"type": "event_msg", "payload": {
            "type": "user_message", "message": "private user message",
            "image": "data:image/png;base64," + ("A" * 10000),
        }},
        {"type": "response_item", "payload": {
            "type": "function_call_output", "output": "huge tool output",
        }},
    ]
    rollout.write_text("".join(json.dumps(item) + "\n" for item in first_records))
    queue = CandidateEventQueue(tmp_path / "memory.db")

    first = import_rollout(rollout, queue)
    second = import_rollout(rollout, queue)
    with rollout.open("a") as handle:
        handle.write(json.dumps({
            "type": "turn_context",
            "payload": {"turn_id": "turn-2", "cwd": "/tmp/project"},
        }) + "\n")
        handle.write(json.dumps({
            "type": "event_msg", "payload": {"type": "task_complete"},
        }) + "\n")
    third = import_rollout(rollout, queue)

    assert first == {"processed": 3, "enqueued": 1}
    assert second == {"processed": 0, "enqueued": 0}
    assert third == {"processed": 2, "enqueued": 0}
    checkpoint = queue.connection.execute(
        "SELECT inode, offset, source_hash FROM import_checkpoints WHERE source_ref=?",
        (str(rollout.resolve()),),
    ).fetchone()
    assert checkpoint[0] == rollout.stat().st_ino
    assert checkpoint[1] == rollout.stat().st_size
    assert len(checkpoint[2]) == 64
    rows = queue.connection.execute(
        "SELECT source_ref, excerpt FROM candidate_events ORDER BY created_at, event_id"
    ).fetchall()
    assert len(rows) == 1
    assert all("#byte=" in row[0] and row[1] is None for row in rows)
    serialized = json.dumps([tuple(row) for row in rows])
    assert "private user message" not in serialized
    assert "base64" not in serialized
    assert "huge tool output" not in serialized


def test_codex_checkpoint_stays_stable_when_small_file_grows(tmp_path):
    from scripts.import_codex_rollouts import import_rollout

    rollout = tmp_path / "small.jsonl"
    rollout.write_text(json.dumps({
        "type": "session_meta", "payload": {"id": "small-session"},
    }) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")
    assert import_rollout(rollout, queue)["processed"] == 1

    with rollout.open("a") as handle:
        handle.write(json.dumps({
            "type": "event_msg", "payload": {"type": "task_complete"},
        }) + "\n")

    assert import_rollout(rollout, queue) == {"processed": 1, "enqueued": 0}


def test_codex_imports_only_explicit_proposal_marker(tmp_path):
    from scripts.import_codex_rollouts import import_rollout

    rollout = tmp_path / "rollout-session-123.jsonl"
    rollout.write_text(json.dumps({
        "type": "response_item",
        "payload": {
            "type": "message",
            "content": "普通正文 DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"持久化规则\"}",
        },
    }) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")

    assert import_rollout(rollout, queue) == {"processed": 1, "enqueued": 1}
    row = queue.connection.execute(
        "SELECT event_type,memory_type,excerpt FROM candidate_events"
    ).fetchone()
    assert tuple(row) == ("memory_proposal", "fact", "持久化规则")


def test_codex_backfills_tail_proposal_after_legacy_checkpoint(tmp_path):
    from scripts.import_codex_rollouts import _fingerprint, import_rollout

    rollout = tmp_path / "legacy.jsonl"
    rollout.write_text(json.dumps({
        "type": "response_item",
        "payload": {"content": "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"旧会话尾部\"}"},
    }) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")
    queue.update_checkpoint(
        str(rollout.resolve()), rollout.stat().st_ino,
        rollout.stat().st_size, _fingerprint(rollout),
    )

    assert import_rollout(rollout, queue) == {"processed": 0, "enqueued": 1}
    assert import_rollout(rollout, queue) == {"processed": 0, "enqueued": 0}


def test_codex_accepts_assistant_output_text_and_ignores_user_marker(tmp_path):
    from scripts.import_codex_rollouts import import_rollout

    rollout = tmp_path / "roles.jsonl"
    records = [
        {"type": "response_item", "payload": {
            "type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"用户注入\"}"}],
        }},
        {"type": "response_item", "payload": {
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"助手结论\"}"}],
        }},
    ]
    rollout.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))
    queue = CandidateEventQueue(tmp_path / "memory.db")

    assert import_rollout(rollout, queue)["enqueued"] == 1
    assert queue.connection.execute(
        "SELECT excerpt FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchone()[0] == "助手结论"


def test_codex_caps_proposals_across_the_whole_tail(tmp_path):
    from scripts.import_codex_rollouts import import_rollout

    rollout = tmp_path / "cap.jsonl"
    records = [{"type": "response_item", "payload": {
        "type": "message", "role": "assistant",
        "content": [{"type": "output_text", "text":
            "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"结论%s\"}" % index}],
    }} for index in range(4)]
    rollout.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))
    queue = CandidateEventQueue(tmp_path / "memory.db")

    import_rollout(rollout, queue)
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchone()[0] == 3
