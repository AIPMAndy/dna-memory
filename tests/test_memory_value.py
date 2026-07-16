import json

from scripts.candidate_events import CandidateEventQueue
from scripts.config import load_config
from scripts.memory_value import memory_value
from scripts.unified_memory import UnifiedMemoryStore


def config(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "knowledge_root": str(tmp_path / "vault"),
        "database_path": str(tmp_path / "memory.db"),
        "backup_dir": str(tmp_path / "backups"),
        "skill_root": str(tmp_path / "skills"),
        "skill_registry": str(tmp_path / "skills.json"),
    }))
    return load_config(profile)


def seed_value_data(config):
    store = UnifiedMemoryStore(config.database_path)
    store.connection.executemany(
        "INSERT INTO memory_recall_events "
        "(query_hash, client, session_id, result_count, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("a" * 64, "codex", "c1", 2, "2026-07-10 12:00:00"),
            ("b" * 64, "claude-desktop", "c2", 0, "2026-06-20 12:00:00"),
            ("c" * 64, "hermes", "h1", 1, "2026-05-01 12:00:00"),
        ],
    )
    store.connection.executemany(
        "INSERT INTO memory_index "
        "(memory_id,type,status,summary,content_hash,clients,created_at,updated_at,source_kind) "
        "VALUES (?, 'fact', 'active', ?, ?, ?, ?, ?, 'markdown')",
        [
            (
                "m1", "private durable summary", "h1", '["codex"]',
                "2026-07-09 12:00:00", "2026-07-09 12:00:00",
            ),
            (
                "m2", "older durable summary", "h2", '["hermes"]',
                "2026-05-01 12:00:00", "2026-05-01 12:00:00",
            ),
        ],
    )
    store.connection.executemany(
        "INSERT INTO memory_feedback "
        "(memory_id,outcome,client,created_at) VALUES (?, ?, ?, ?)",
        [
            ("m1", "useful", "claude", "2026-07-10 12:00:00"),
            ("m2", "misleading", "hermes-cli", "2026-06-20 12:00:00"),
        ],
    )
    store.connection.commit()
    store.close()

    queue = CandidateEventQueue(config.database_path)
    for event_id in ("h1", "h2"):
        queue.enqueue({
            "event_id": event_id,
            "client": "hermes-desktop",
            "event_type": "session_updated",
        })
    queue.connection.execute(
        "UPDATE candidate_events SET created_at='2026-07-08 12:00:00'"
    )
    queue.connection.commit()
    queue.connection.close()

    config.backup_dir.mkdir(parents=True)
    (config.backup_dir / "memory-test.db").write_bytes(b"backup")


def test_memory_value_aggregates_windows_clients_backlog_and_storage(tmp_path):
    cfg = config(tmp_path)
    seed_value_data(cfg)

    payload = memory_value(cfg, now="2026-07-11 12:00:00")

    assert payload["all_time"] == {
        "recall_attempts": 3,
        "recall_hits": 2,
        "hit_rate": 2 / 3,
        "returned_memories": 3,
        "useful": 1,
        "misleading": 1,
        "unfeedback": 1,
        "new_memories": 2,
    }
    assert payload["windows"]["7d"]["new_memories"] == 1
    assert payload["windows"]["7d"]["recall_attempts"] == 1
    assert payload["windows"]["30d"]["recall_attempts"] == 2
    assert payload["clients"]["hermes"]["candidate_events"] == 2
    assert payload["clients"]["hermes"]["misleading"] == 1
    assert payload["clients"]["claude"]["recall_attempts"] == 1
    assert payload["clients"]["codex"]["new_memories"] == 1
    assert payload["backlog"] == {
        "pending": 2, "oldest_pending_at": "2026-07-08 12:00:00"
    }
    assert payload["storage"]["database_bytes"] > 0
    assert payload["storage"]["backup_bytes"] == 6
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "private durable summary" not in serialized
    assert str(cfg.database_path) not in serialized


def test_memory_value_returns_zeros_without_a_database(tmp_path):
    payload = memory_value(config(tmp_path), now="2026-07-11 12:00:00")

    assert payload["all_time"]["recall_attempts"] == 0
    assert payload["clients"]["codex"]["candidate_events"] == 0
    assert payload["backlog"]["oldest_pending_at"] is None


def test_memory_value_windows_accept_iso_offsets_and_unix_seconds(tmp_path):
    cfg = config(tmp_path)
    store = UnifiedMemoryStore(cfg.database_path)
    rows = [
        ("iso-basic", "2026-07-10T12:00:00+0800"),
        ("iso-colon", "2026-07-10T12:00:00+08:00"),
        ("sqlite", "2026-07-10 04:00:00"),
        ("unix", 1783656000),
        ("old", "2026-05-01T12:00:00+0800"),
        ("invalid", "not-a-time"),
    ]
    store.connection.executemany(
        "INSERT INTO memory_index "
        "(memory_id,type,status,summary,content_hash,clients,created_at,updated_at,source_kind) "
        "VALUES (?, 'fact', 'active', ?, ?, '[\"codex\"]', ?, ?, 'markdown')",
        [(name, name, name, created_at, created_at) for name, created_at in rows],
    )
    store.connection.commit()
    store.close()

    payload = memory_value(cfg, now="2026-07-11T12:00:00+0800")

    assert payload["all_time"]["new_memories"] == 6
    assert payload["windows"]["7d"]["new_memories"] == 4
