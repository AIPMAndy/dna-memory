import json
import os
import time

import pytest

import scripts.import_native_history as native_history
from scripts.candidate_events import CandidateEventQueue
from scripts.import_native_history import (
    SourceSpec,
    import_paths,
    prune_obsolete_sources,
)


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
    assert second == {
        "files": 0,
        "processed": 0,
        "enqueued": 0,
        "proposals": 0,
        "errors": 0,
        "proposal_types": {},
        "error_types": {},
    }


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


def test_history_import_counts_bad_file_and_continues(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    root.mkdir()
    bad = root / "a_bad.jsonl"
    good = root / "b_good.jsonl"
    bad.write_text("invalid native record\n")
    good.write_text(json.dumps({
        "role": "user",
        "content": "以后必须先验证再发布。",
    }, ensure_ascii=False) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")
    real_import = native_history.import_native_file

    def import_or_fail(path, *args, **kwargs):
        if path.name == bad.name:
            raise ValueError("invalid native record")
        return real_import(path, *args, **kwargs)

    monkeypatch.setattr(native_history, "import_native_file", import_or_fail)

    result = import_paths(
        {"hermes": SourceSpec((root,), ("*.jsonl",))},
        queue,
        max_files=10,
        min_age_seconds=0,
    )

    assert result["files"] == 2
    assert result["processed"] == 1
    assert result["proposals"] == 1
    assert result["errors"] == 1
    assert result["error_types"] == {"hermes:jsonl:ValueError": 1}
    serialized = json.dumps(result, ensure_ascii=False)
    assert str(bad) not in serialized
    assert "invalid native record" not in serialized


def test_reextract_days_forces_only_recent_files_and_remains_idempotent(tmp_path):
    root = tmp_path / "native"
    root.mkdir()
    recent = root / "recent.jsonl"
    old = root / "old.jsonl"
    recent.write_text(json.dumps({
        "role": "user",
        "content": "最终决定采用最近七天有界回填方案。",
    }, ensure_ascii=False) + "\n")
    old.write_text(json.dumps({
        "role": "user",
        "content": "最终决定采用旧历史全量回填方案。",
    }, ensure_ascii=False) + "\n")
    now = time.time() - 300
    os.utime(recent, (now - 86400, now - 86400))
    os.utime(old, (now - 10 * 86400, now - 10 * 86400))
    queue = CandidateEventQueue(tmp_path / "memory.db")
    paths = {"codex": SourceSpec((root,), ("*.jsonl",))}
    initial = import_paths(paths, queue, max_files=10, min_age_seconds=0, now=now)
    assert initial["files"] == 2
    row_count = queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events"
    ).fetchone()[0]

    first = import_paths(
        paths,
        queue,
        max_files=10,
        min_age_seconds=0,
        reextract_days=7,
        now=now,
    )
    second = import_paths(
        paths,
        queue,
        max_files=10,
        min_age_seconds=0,
        reextract_days=7,
        now=now,
    )

    assert first["files"] == 1
    assert first["processed"] == 1
    assert first["proposals"] == 1
    assert first["enqueued"] == 0
    assert second["files"] == 1
    assert second["enqueued"] == 0
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events"
    ).fetchone()[0] == row_count


def test_backtest_uses_separate_database_and_returns_aggregate_metrics(tmp_path):
    root = tmp_path / "native"
    root.mkdir()
    source = root / "recent.jsonl"
    source.write_text(json.dumps({
        "role": "assistant",
        "content": "已验证：scripts/native_auto_extract.py 可写入隔离回测队列。",
    }, ensure_ascii=False) + "\n")
    now = time.time() - 300
    os.utime(source, (now - 3600, now - 3600))
    production_path = tmp_path / "production.db"
    production = CandidateEventQueue(production_path)
    production.update_checkpoint("production-checkpoint", 1, 2, "unchanged")
    production.connection.close()
    production_bytes = production_path.read_bytes()
    backtest_path = tmp_path / "backtest.db"

    result = native_history.run_backtest(
        {"codex": SourceSpec((root,), ("*.jsonl",))},
        backtest_path,
        days=7,
        max_files=10,
        min_age_seconds=0,
        now=now,
    )

    assert result == {
        "mode": "backtest",
        "files": 1,
        "processed": 1,
        "enqueued": 1,
        "proposals": 1,
        "errors": 0,
        "proposal_types": {"fact": 1},
        "error_types": {},
    }
    assert production_path.read_bytes() == production_bytes
    backtest = CandidateEventQueue(backtest_path)
    try:
        assert backtest.connection.execute(
            "SELECT COUNT(*) FROM candidate_events WHERE event_type='memory_proposal'"
        ).fetchone()[0] == 1
    finally:
        backtest.connection.close()
    serialized = json.dumps(result, ensure_ascii=False)
    assert str(source) not in serialized
    assert "可写入隔离回测队列" not in serialized


def test_backtest_rejects_existing_nonempty_database(tmp_path):
    database = tmp_path / "existing.db"
    database.write_bytes(b"not a fresh sqlite database")

    with pytest.raises(ValueError, match="new or empty"):
        native_history.run_backtest({}, database, days=7)


def test_backtest_cli_requires_days_and_database_together():
    with pytest.raises(SystemExit) as error:
        native_history.main(["--backtest-days", "7"])

    assert error.value.code == 2
