import json
import sqlite3

from scripts.candidate_events import CandidateEventQueue
from scripts.config import load_config
from scripts.memory_cli import main
from scripts.unified_memory import UnifiedMemoryStore


def profile_file(tmp_path, **overrides):
    vault = tmp_path / "vault"
    vault.mkdir()
    profile = tmp_path / "profile.json"
    values = {
        "knowledge_root": str(vault),
        "database_path": str(tmp_path / "memory.db"),
        "skill_root": str(tmp_path / "shared"),
        "skill_registry": str(tmp_path / "skills.json"),
    }
    values.update(overrides)
    profile.write_text(json.dumps(values))
    return profile, vault


def seed_cli_value_data(config):
    store = UnifiedMemoryStore(config.database_path)
    store.connection.execute(
        "INSERT INTO memory_recall_events "
        "(query_hash,client,result_count,created_at) VALUES (?, 'codex', 1, ?)",
        ("a" * 64, "2026-07-10 12:00:00"),
    )
    store.connection.commit()
    store.close()
    queue = CandidateEventQueue(config.database_path)
    queue.enqueue({
        "event_id": "h1", "client": "hermes", "event_type": "session_updated"
    })
    queue.connection.close()


def test_memory_status_outputs_json(tmp_path, capsys):
    profile, _ = profile_file(tmp_path)

    assert main(["--profile", str(profile), "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["truth_root_exists"] is True
    assert payload["capacity"]["state"] == "ok"
    assert payload["managed_records"] == 0


def test_memory_reindex_reports_counts(tmp_path, capsys):
    profile, vault = profile_file(tmp_path)
    (vault / "note.md").write_text("# ordinary")

    assert main(["--profile", str(profile), "reindex", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {"indexed": 0, "removed": 0, "scanned": 1, "skipped": 1}


def test_memory_reindex_stops_at_database_hard_limit(tmp_path, capsys):
    database = tmp_path / "memory.db"
    database.write_bytes(b"already too large")
    profile, _ = profile_file(tmp_path, hard_bytes=1, warning_bytes=0)

    assert main(["--profile", str(profile), "reindex", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)

    assert payload["error"] == "capacity_blocked"


def test_record_limit_is_warning_not_write_block(tmp_path, capsys):
    profile, _ = profile_file(tmp_path, max_records=0)

    assert main(["--profile", str(profile), "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["capacity"]["state"] == "warning"
    assert payload["capacity"]["writable"] is True


def test_memory_maintain_daily_outputs_bounded_json(tmp_path, capsys):
    profile, _ = profile_file(tmp_path)

    assert main([
        "--profile", str(profile), "maintain", "daily", "--json",
        "--now", "2026-07-11 12:00:00",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "compacted": 0, "crystallized": 0, "deleted": 0,
        "expired": 0, "rejected": 0,
    }


def test_memory_value_outputs_bounded_json(tmp_path, capsys):
    profile, _ = profile_file(tmp_path, backup_dir=str(tmp_path / "backups"))
    seed_cli_value_data(load_config(profile))

    assert main([
        "--profile", str(profile), "value", "--json",
        "--now", "2026-07-11 12:00:00",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["all_time"]["recall_attempts"] == 1
    assert payload["clients"]["hermes"]["candidate_events"] == 1
    assert "private durable summary" not in json.dumps(payload)


def test_memory_coverage_distinguishes_native_and_explicit_surfaces(
        tmp_path, capsys, monkeypatch):
    hermes_db = tmp_path / "state.db"
    connection = sqlite3.connect(hermes_db)
    connection.execute(
        "CREATE TABLE sessions "
        "(id TEXT PRIMARY KEY, source TEXT NOT NULL, started_at REAL NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO sessions VALUES (?, ?, 1)",
        (("h-cli", "cli"), ("h-tui", "tui"), ("h-feishu", "feishu")),
    )
    connection.commit()
    connection.close()
    profile, _ = profile_file(tmp_path, hermes_state_db=str(hermes_db))
    codex = tmp_path / ".codex" / "sessions"
    codex.mkdir(parents=True)
    codex_desktop = codex / "desktop.jsonl"
    codex_desktop.write_text(json.dumps({
        "type": "session_meta",
        "payload": {
            "originator": "Codex Desktop",
            "source": {"subagent": {"thread_spawn": {"parent_thread_id": "private"}}},
        },
    }) + "\n")
    codex_cli = codex / "cli.jsonl"
    codex_cli.write_text(json.dumps({
        "type": "session_meta",
        "payload": {"originator": "codex-tui", "source": "cli"},
    }) + "\n")
    claude = tmp_path / ".claude" / "projects"
    claude.mkdir(parents=True)
    claude_desktop = claude / "desktop.jsonl"
    claude_desktop.write_text(json.dumps({"entrypoint": "claude-desktop-3p"}) + "\n")
    claude_cli = claude / "cli.jsonl"
    claude_cli.write_text(json.dumps({"entrypoint": "sdk-cli"}) + "\n")
    claude_sdk = claude / "sdk.jsonl"
    claude_sdk.write_text(json.dumps({"entrypoint": "sdk-ts"}) + "\n")
    from scripts.candidate_events import CandidateEventQueue
    from scripts.import_native_history import SourceSpec
    from scripts import client_coverage

    queue = CandidateEventQueue(tmp_path / "memory.db")
    for client, session in (
        ("codex", codex_desktop), ("codex", codex_cli),
        ("claude-code", claude_desktop), ("claude-code", claude_cli),
        ("claude-code", claude_sdk),
    ):
        stat = session.stat()
        queue.update_checkpoint(
            "native-auto:{}:{}".format(client, session.resolve()),
            stat.st_ino, stat.st_size, "digest",
        )
    for session_id in ("h-cli", "h-tui", "h-feishu"):
        queue.update_checkpoint(
            "hermes:{}#{}".format(hermes_db.resolve(), session_id), 0, 0, "digest"
        )
    queue.connection.close()
    monkeypatch.setattr(client_coverage, "configured_paths", lambda config: {
        "codex": SourceSpec((codex,), ("*.jsonl",)),
        "claude-code": SourceSpec((claude,), ("*.jsonl",)),
    })
    monkeypatch.setattr(client_coverage, "_launch_agent", lambda home, label: {
        "installed": True, "loaded": True, "last_exit_code": 0,
    })

    assert main(["--profile", str(profile), "coverage", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["surfaces"]["codex-desktop"]["entry_evidence"]["verified"] is True
    assert payload["surfaces"]["codex-desktop"]["entry_evidence"]["matched_files"] == 1
    assert payload["surfaces"]["codex-desktop"]["entry_evidence"]["markers"] == {
        "Codex Desktop/subagent": 1,
    }
    assert payload["surfaces"]["codex-desktop"]["source"]["checkpointed_files"] == 1
    assert payload["surfaces"]["codex-cli"]["entry_evidence"]["verified"] is True
    assert payload["surfaces"]["codex-cli"]["entry_evidence"]["matched_files"] == 1
    assert payload["surfaces"]["codex-cli"]["source"]["checkpointed_files"] == 1
    assert payload["surfaces"]["claude-code-desktop"]["entry_evidence"] == {
        "verified": True,
        "matched_files": 1,
        "markers": {"claude-desktop-3p": 1},
    }
    assert payload["surfaces"]["claude-code-cli"]["entry_evidence"] == {
        "verified": True,
        "matched_files": 1,
        "markers": {"sdk-cli": 1},
    }
    assert payload["native_sources"]["claude-code"]["unclassified_files"] == 1
    assert payload["surfaces"]["hermes-desktop"]["entry_evidence"]["verified"] is False
    assert payload["surfaces"]["hermes-desktop"]["entry_evidence"]["matched_sessions"] == 0
    assert payload["surfaces"]["hermes-cli"]["entry_evidence"] == {
        "verified": True,
        "matched_sessions": 2,
        "markers": {"cli": 1, "tui": 1},
    }
    assert payload["surfaces"]["hermes-gateway"]["entry_evidence"]["matched_sessions"] == 1
    assert payload["surfaces"]["claude-desktop-cloud"]["automatic_capture"] is False
    assert payload["surfaces"]["claude-desktop-cloud"]["capture_mode"] == "explicit-mcp-writeback"
