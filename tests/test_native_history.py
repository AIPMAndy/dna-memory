import json

from scripts.candidate_events import CandidateEventQueue
from scripts.import_native_history import SourceSpec, import_paths, prune_obsolete_sources


def test_history_import_scans_supported_sources_with_file_budget(tmp_path):
    codex = tmp_path / "codex"
    hermes = tmp_path / "hermes"
    codex.mkdir()
    hermes.mkdir()
    (codex / "a.jsonl").write_text(json.dumps({
        "type": "response_item", "payload": {
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": "已验证：Codex 规则生效。"}],
        },
    }) + "\n")
    (hermes / "b.jsonl").write_text(json.dumps({
        "role": "user", "content": "以后必须先检查再发布。",
    }) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")

    result = import_paths(
        {"codex": [codex], "hermes": [hermes]}, queue,
        max_files=1, min_age_seconds=0,
    )

    assert result["files"] == 2
    assert result["processed"] == 2
    assert result["proposals"] == 2

    second = import_paths(
        {"codex": [codex], "hermes": [hermes]}, queue,
        max_files=1, min_age_seconds=0,
    )
    assert second == {"files": 0, "processed": 0, "enqueued": 0, "proposals": 0}


def test_history_import_uses_explicit_client_source_specs(tmp_path):
    claude = tmp_path / "claude"
    desktop = tmp_path / "desktop"
    hermes = tmp_path / "hermes"
    for path in (claude, desktop, hermes):
        path.mkdir()
    message = json.dumps({"role": "user", "content": "以后必须先验证再发布。"}) + "\n"
    (claude / "real.jsonl").write_text(message)
    (claude / "tool-result.json").write_text(message)
    (desktop / "audit.jsonl").write_text(message)
    (desktop / "other.jsonl").write_text(message)
    (hermes / "session_live.json").write_text(json.dumps({
        "session_id": "live", "messages": [
            {"role": "user", "content": "以后必须先验证再发布。"},
        ],
    }))
    (hermes / "request_dump_private.json").write_text(message)
    queue = CandidateEventQueue(tmp_path / "memory.db")

    result = import_paths({
        "claude-code": SourceSpec((claude,), ("*.jsonl",)),
        "claude-desktop": SourceSpec((desktop,), ("audit.jsonl",)),
        "hermes": SourceSpec((hermes,), ("*.jsonl", "session_*.json")),
    }, queue, max_files=10, min_age_seconds=0)

    assert result["files"] == 3
    sources = {
        row[0] for row in queue.connection.execute(
            "SELECT DISTINCT source_ref FROM candidate_events"
        ).fetchall()
    }
    assert not any("tool-result.json" in source for source in sources)
    assert not any("other.jsonl" in source for source in sources)
    assert not any("request_dump" in source for source in sources)


def test_prune_obsolete_removes_only_auto_events_for_invalid_sources(tmp_path):
    root = tmp_path / "claude"
    root.mkdir()
    valid = root / "valid.jsonl"
    invalid = root / "tool-result.json"
    valid.write_text("{}\n")
    invalid.write_text("{}\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")
    for path in (valid, invalid):
        stat = path.stat()
        queue.update_checkpoint(
            "native-auto:claude-code:" + str(path.resolve()),
            stat.st_ino, stat.st_size, "digest",
        )
        queue.enqueue({
            "event_id": "auto_session_" + path.stem,
            "client": "claude-code",
            "event_type": "session_updated",
            "source_ref": str(path.resolve()),
            "source_hash": "digest",
        })
    queue.enqueue({
        "event_id": "manual-pointer",
        "client": "claude-code",
        "event_type": "session_updated",
        "source_ref": str(invalid.resolve()),
        "source_hash": "manual",
    })

    result = prune_obsolete_sources({
        "claude-code": SourceSpec((root,), ("*.jsonl",)),
    }, queue)

    assert result == {"checkpoints": 1, "events": 1}
    assert queue.get_checkpoint("native-auto:claude-code:" + str(valid.resolve()))
    assert queue.get_checkpoint("native-auto:claude-code:" + str(invalid.resolve())) is None
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events WHERE event_id='manual-pointer'"
    ).fetchone()[0] == 1
