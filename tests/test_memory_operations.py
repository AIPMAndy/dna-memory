import json
from pathlib import Path

from scripts.candidate_events import CandidateEventQueue
from scripts.config import load_config
from scripts.memory_operations import MemoryOperations


def _profile(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "knowledge_root": str(tmp_path / "vault"),
        "managed_memory_dir": "00 System/Memory",
        "database_path": str(tmp_path / "memory.db"),
        "skill_root": str(tmp_path / "skills"),
        "skill_registry": str(tmp_path / "skills.json"),
        "backup_dir": str(tmp_path / "backups"),
        "backup_keep": 2,
    }))
    return load_config(profile)


def test_only_reviewed_safe_proposals_crystallize(tmp_path):
    config = _profile(tmp_path)
    queue = CandidateEventQueue(config.database_path)
    queue.enqueue({
        "event_id": "proposal-1", "client": "codex",
        "event_type": "memory_proposal", "memory_type": "decision",
        "excerpt": "统一记忆只保存经过验证的结论",
        "source_ref": "codex://session/turn", "confidence": "high",
        "importance": 0.9,
    })
    queue.enqueue({
        "event_id": "pointer-1", "client": "codex",
        "event_type": "task_complete", "source_ref": "/tmp/session.jsonl#byte=1",
    })

    result = MemoryOperations(config).daily(now="2026-07-11 12:00:00")

    assert result["crystallized"] == 1
    assert result["deduplicated"] == 0
    assert result["rejected"] == 0
    rows = queue.connection.execute(
        "SELECT event_id, status, memory_id FROM candidate_events ORDER BY event_id"
    ).fetchall()
    assert rows[0][1] == "pending"
    assert rows[1][1] == "crystallized"
    assert rows[1][2]
    pages = list((config.knowledge_root / config.managed_memory_dir).glob("*.md"))
    assert len(pages) == 1
    assert "统一记忆只保存经过验证的结论" in pages[0].read_text()


def test_invalid_proposal_is_rejected_without_markdown(tmp_path):
    config = _profile(tmp_path)
    queue = CandidateEventQueue(config.database_path)
    queue.enqueue({
        "event_id": "bad", "client": "claude",
        "event_type": "memory_proposal", "memory_type": "invalid",
        "excerpt": "不能成为长期记忆",
    })

    result = MemoryOperations(config).daily(now="2026-07-11 12:00:00")

    assert result["rejected"] == 1
    row = queue.connection.execute(
        "SELECT status, error FROM candidate_events WHERE event_id='bad'"
    ).fetchone()
    assert row[0] == "rejected"
    assert "type" in row[1]
    assert not (config.knowledge_root / config.managed_memory_dir).exists()


def test_daily_rejects_invalid_then_crystallizes_valid_without_locking(tmp_path):
    config = _profile(tmp_path)
    queue = CandidateEventQueue(config.database_path)
    queue.enqueue({
        "event_id": "bad-first", "client": "claude",
        "event_type": "memory_proposal", "memory_type": "invalid",
        "excerpt": "不能成为长期记忆",
    })
    queue.enqueue({
        "event_id": "good-second", "client": "codex",
        "event_type": "memory_proposal", "memory_type": "workflow",
        "excerpt": "候选拒绝后仍应继续结晶同批次的有效记忆",
        "source_ref": "codex://session/verified", "confidence": "high",
        "importance": 0.8,
    })

    result = MemoryOperations(config).daily(now="2026-07-12 12:00:00")

    assert result["rejected"] == 1
    assert result["crystallized"] == 1
    assert result["deduplicated"] == 0
    rows = dict(queue.connection.execute(
        "SELECT event_id, status FROM candidate_events ORDER BY event_id"
    ).fetchall())
    assert rows == {"bad-first": "rejected", "good-second": "crystallized"}
    pages = list((config.knowledge_root / config.managed_memory_dir).glob("*.md"))
    assert len(pages) == 1
    assert "同批次的有效记忆" in pages[0].read_text()


def test_daily_marks_cross_session_duplicate_as_deduplicated(tmp_path):
    config = _profile(tmp_path)
    queue = CandidateEventQueue(config.database_path)
    for event_id, client, source_ref in (
        ("proposal-a", "codex", "codex://session/a"),
        ("proposal-b", "hermes", "hermes://session/b"),
    ):
        queue.enqueue({
            "event_id": event_id, "client": client,
            "event_type": "memory_proposal", "memory_type": "fact",
            "excerpt": "metaver.vip 当前返回 200",
            "source_ref": source_ref, "source_hash": "source-" + event_id,
        })

    result = MemoryOperations(config).daily(now="2026-07-12 12:00:00")

    assert result["crystallized"] == 1
    assert result["deduplicated"] == 1
    rows = dict(queue.connection.execute(
        "SELECT event_id, status FROM candidate_events ORDER BY event_id"
    ).fetchall())
    assert rows == {"proposal-a": "crystallized", "proposal-b": "deduplicated"}


def test_retention_expires_pointers_and_deletes_terminal_events(tmp_path):
    config = _profile(tmp_path)
    queue = CandidateEventQueue(config.database_path)
    queue.enqueue({"event_id": "old-pointer", "client": "codex", "event_type": "Stop"})
    queue.enqueue({"event_id": "old-done", "client": "claude", "event_type": "Stop"})
    queue.connection.execute(
        "UPDATE candidate_events SET created_at='2026-05-01 00:00:00' WHERE event_id='old-pointer'"
    )
    queue.connection.execute(
        "UPDATE candidate_events SET status='crystallized', processed_at='2026-05-01 00:00:00' "
        "WHERE event_id='old-done'"
    )
    queue.connection.commit()

    result = MemoryOperations(config).daily(now="2026-07-11 12:00:00")

    assert result["expired"] == 1
    assert result["deleted"] == 1
    assert queue.connection.execute(
        "SELECT status FROM candidate_events WHERE event_id='old-pointer'"
    ).fetchone()[0] == "expired"
    assert queue.connection.execute(
        "SELECT 1 FROM candidate_events WHERE event_id='old-done'"
    ).fetchone() is None


def test_daily_compacts_codex_turn_events_when_session_pointer_exists(tmp_path):
    config = _profile(tmp_path)
    queue = CandidateEventQueue(config.database_path)
    queue.enqueue({
        "event_id": "session", "client": "codex", "event_type": "session_meta",
        "session_id": "s1", "source_ref": "/tmp/rollout.jsonl#byte=0",
    })
    queue.enqueue({
        "event_id": "turn", "client": "codex", "event_type": "turn_context",
        "session_id": "s1", "source_ref": "/tmp/rollout.jsonl#byte=10",
    })
    queue.enqueue({
        "event_id": "orphan", "client": "codex", "event_type": "task_complete",
        "session_id": "missing", "source_ref": "/tmp/orphan.jsonl#byte=10",
    })

    result = MemoryOperations(config).daily(now="2026-07-12 12:00:00")

    assert result["compacted"] == 1
    rows = dict(queue.connection.execute(
        "SELECT event_id, status FROM candidate_events"
    ).fetchall())
    assert rows == {"session": "pending", "turn": "superseded", "orphan": "pending"}


def test_weekly_backup_rotation_and_monthly_integrity(tmp_path):
    config = _profile(tmp_path)
    operations = MemoryOperations(config)
    for stamp in ("20260101T000000", "20260201T000000", "20260301T000000"):
        result = operations.weekly(now="2026-07-11 12:00:00", backup_stamp=stamp)
        assert Path(result["backup_path"]).is_file()
    assert len(list(config.backup_dir.glob("memory-*.db"))) == 2

    monthly = operations.monthly(now="2026-07-11 12:00:00", backup_stamp="20260401T000000")
    assert monthly["integrity"] == "ok"
    assert monthly["reindex"]["scanned"] == 0
