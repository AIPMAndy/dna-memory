import json

import pytest

from scripts.config import load_config
from scripts.memory_service import MemoryService, MemoryValidationError


def service(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "knowledge_root": str(tmp_path / "vault"),
        "managed_memory_dir": "00 System/Memory",
        "database_path": str(tmp_path / "memory.db"),
        "skill_root": str(tmp_path / "skills"),
        "skill_registry": str(tmp_path / "registry.json"),
    }))
    return MemoryService(load_config(profile))


def test_remember_writes_truth_and_is_immediately_recallable(tmp_path):
    svc = service(tmp_path)
    result = svc.remember({
        "type": "preference", "summary": "偏好唯一标识 XQ91",
        "source_hash": "source-1", "confidence": "high", "importance": 0.9,
        "clients": ["claude"],
    })
    recalled = svc.recall("XQ91")
    assert result["created"] is True
    assert recalled[0]["memory_id"] == result["memory_id"]
    assert list((tmp_path / "vault/00 System/Memory").glob("*.md"))


def test_source_hash_is_idempotent(tmp_path):
    svc = service(tmp_path)
    proposal = {"type": "fact", "summary": "same", "source_hash": "stable"}
    first = svc.remember(proposal)
    second = svc.remember(proposal)
    assert second == {
        "created": False, "deduplicated": True,
        "memory_id": first["memory_id"], "superseded": [],
    }


def test_normalized_active_summary_deduplicates_and_merges_provenance(tmp_path):
    svc = service(tmp_path)
    first = svc.remember({
        "type": "fact",
        "summary": "飞书表格入口已可直接打开",
        "source_refs": ["codex://session/one"],
        "clients": ["codex"],
    })

    second = svc.remember({
        "type": "fact",
        "summary": "  飞书表格入口已可直接打开  ",
        "source_refs": ["hermes://session/two"],
        "clients": ["hermes"],
    })

    assert second == {
        "created": False, "deduplicated": True,
        "memory_id": first["memory_id"], "superseded": [],
    }
    record = svc.get(first["memory_id"])
    assert record["source_refs"] == ["codex://session/one", "hermes://session/two"]
    assert record["clients"] == ["codex", "hermes"]
    assert len(list((tmp_path / "vault/00 System/Memory").glob("*.md"))) == 1


def test_deduplication_is_scoped_to_type_and_active_status(tmp_path):
    svc = service(tmp_path)
    fact = svc.remember({"type": "fact", "summary": "same scoped conclusion"})
    decision = svc.remember({"type": "decision", "summary": "same scoped conclusion"})

    assert decision["created"] is True
    svc.store.connection.execute(
        "UPDATE memory_index SET status='superseded' WHERE memory_id=?",
        (fact["memory_id"],),
    )
    svc.store.connection.commit()
    replacement = svc.remember({"type": "fact", "summary": "same scoped conclusion"})
    assert replacement["created"] is True


def test_sensitive_proposal_is_rejected(tmp_path):
    svc = service(tmp_path)
    with pytest.raises(MemoryValidationError):
        svc.remember({"type": "fact", "summary": "password=secret123"})


def test_multi_term_recall_ranks_hits_and_records_telemetry(tmp_path):
    svc = service(tmp_path)
    both = svc.remember({
        "type": "fact", "summary": "Claude Hermes Desktop adapter",
        "importance": 0.5,
    })
    svc.remember({
        "type": "fact", "summary": "Claude Desktop memory migration",
        "importance": 0.9,
    })
    svc.remember({
        "type": "fact", "summary": "Hermes memory adapter",
        "importance": 0.8,
    })

    rows = svc.recall(
        "Claude, Hermes Desktop", client="codex", session_id="session-1"
    )

    assert rows[0]["memory_id"] == both["memory_id"]
    assert {row["summary"] for row in rows} == {
        "Claude Hermes Desktop adapter",
        "Claude Desktop memory migration",
        "Hermes memory adapter",
    }
    event = svc.store.connection.execute(
        "SELECT client, session_id, result_count, length(query_hash) "
        "FROM memory_recall_events"
    ).fetchone()
    assert tuple(event) == ("codex", "session-1", 3, 64)
    counts = svc.store.connection.execute(
        "SELECT recall_count, last_recalled_at FROM memory_index"
    ).fetchall()
    assert all(row[0] == 1 and row[1] for row in counts)


def test_recall_uses_feedback_then_confidence_as_tiebreakers(tmp_path):
    svc = service(tmp_path)
    useful = svc.remember({
        "type": "fact", "summary": "shared ranking useful", "confidence": "low",
        "importance": 0.1,
    })
    high = svc.remember({
        "type": "fact", "summary": "shared ranking high", "confidence": "high",
        "importance": 0.9,
    })
    svc.remember({
        "type": "fact", "summary": "shared ranking medium", "confidence": "medium"
    })
    svc.feedback(useful["memory_id"], "useful")

    rows = svc.recall("shared ranking")

    assert [row["summary"] for row in rows] == [
        "shared ranking useful", "shared ranking high", "shared ranking medium"
    ]


def test_recall_rejects_empty_or_punctuation_only_query(tmp_path):
    svc = service(tmp_path)
    with pytest.raises(MemoryValidationError, match="query is required"):
        svc.recall(" , 。 ")


def test_remember_supersedes_multiple_active_memories_and_hides_them_from_recall(tmp_path):
    svc = service(tmp_path)
    old_a = svc.remember({"type": "project_state", "summary": "obsolete alpha unique"})
    old_b = svc.remember({"type": "project_state", "summary": "obsolete beta unique"})

    result = svc.remember({
        "type": "project_state",
        "summary": "current verified state",
        "supersedes": [
            old_a["memory_id"], old_b["memory_id"], old_a["memory_id"],
        ],
    })

    assert result["superseded"] == [old_a["memory_id"], old_b["memory_id"]]
    current = svc.get(result["memory_id"])
    assert current["supersedes"] == [old_a["memory_id"], old_b["memory_id"]]
    assert current["superseded_by"] is None
    for old in (old_a, old_b):
        record = svc.get(old["memory_id"])
        assert record["status"] == "superseded"
        assert record["superseded_by"] == result["memory_id"]
    assert svc.recall("obsolete unique") == []


@pytest.mark.parametrize("supersedes", ["mem_old", [""], ["missing-memory"]])
def test_invalid_supersedes_leave_markdown_unchanged(tmp_path, supersedes):
    svc = service(tmp_path)
    old = svc.remember({"type": "fact", "summary": "stable old fact"})
    if supersedes == "mem_old":
        supersedes = old["memory_id"]
    root = tmp_path / "vault/00 System/Memory"
    before = {path.name: path.read_text() for path in root.glob("*.md")}

    with pytest.raises(MemoryValidationError):
        svc.remember({
            "type": "fact", "summary": "must not be written",
            "supersedes": supersedes,
        })

    after = {path.name: path.read_text() for path in root.glob("*.md")}
    assert after == before


def test_source_hash_idempotency_does_not_repeat_supersede(tmp_path):
    svc = service(tmp_path)
    old = svc.remember({"type": "fact", "summary": "old idempotent state"})
    proposal = {
        "type": "fact", "summary": "new idempotent state",
        "source_hash": "supersede-idempotency",
        "supersedes": [old["memory_id"]],
    }

    first = svc.remember(proposal)
    old_path = tmp_path / "vault/00 System/Memory" / (old["memory_id"] + ".md")
    after_first = old_path.read_text()
    second = svc.remember(proposal)

    assert first["superseded"] == [old["memory_id"]]
    assert second == {
        "created": False, "deduplicated": True,
        "memory_id": first["memory_id"], "superseded": [],
    }
    assert old_path.read_text() == after_first


def test_supersede_rejects_non_active_or_non_markdown_targets(tmp_path):
    svc = service(tmp_path)
    old = svc.remember({"type": "fact", "summary": "target lifecycle state"})
    svc.store.connection.execute(
        "UPDATE memory_index SET status='archived' WHERE memory_id=?",
        (old["memory_id"],),
    )
    svc.store.connection.commit()

    with pytest.raises(MemoryValidationError, match="not active"):
        svc.remember({
            "type": "fact", "summary": "invalid archived replacement",
            "supersedes": [old["memory_id"]],
        })

    svc.store.connection.execute(
        "UPDATE memory_index SET status='active', source_kind='legacy_cache' "
        "WHERE memory_id=?", (old["memory_id"],),
    )
    svc.store.connection.commit()
    with pytest.raises(MemoryValidationError, match="not Markdown-managed"):
        svc.remember({
            "type": "fact", "summary": "invalid legacy replacement",
            "supersedes": [old["memory_id"]],
        })


def test_file_install_failure_rolls_back_all_markdown_and_index(tmp_path, monkeypatch):
    svc = service(tmp_path)
    old_a = svc.remember({"type": "project_state", "summary": "rollback alpha"})
    old_b = svc.remember({"type": "project_state", "summary": "rollback beta"})
    root = tmp_path / "vault/00 System/Memory"
    before = {path.name: path.read_text() for path in root.glob("*.md")}
    real_replace = __import__("scripts.memory_service", fromlist=["os"]).os.replace
    install_count = 0

    def fail_second_install(source, destination):
        nonlocal install_count
        if str(destination).endswith(".md") and str(source).endswith(".tmp"):
            install_count += 1
            if install_count == 2:
                raise OSError("injected install failure")
        return real_replace(source, destination)

    monkeypatch.setattr("scripts.memory_service.os.replace", fail_second_install)

    with pytest.raises(OSError, match="injected install failure"):
        svc.remember({
            "type": "project_state", "summary": "must roll back",
            "supersedes": [old_a["memory_id"], old_b["memory_id"]],
        })

    after = {path.name: path.read_text() for path in root.glob("*.md")}
    assert after == before
    assert not list(root.glob(".*.tmp"))
    assert not list(root.glob(".*.bak"))
    assert svc.get(old_a["memory_id"])["status"] == "active"
    assert svc.get(old_b["memory_id"])["status"] == "active"


def test_reindex_failure_restores_markdown_and_rebuilds_previous_index(tmp_path, monkeypatch):
    svc = service(tmp_path)
    old = svc.remember({"type": "project_state", "summary": "reindex rollback"})
    root = tmp_path / "vault/00 System/Memory"
    before = {path.name: path.read_text() for path in root.glob("*.md")}
    module = __import__("scripts.memory_service", fromlist=["reindex_markdown"])
    real_reindex = module.reindex_markdown
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected reindex failure")
        return real_reindex(*args, **kwargs)

    monkeypatch.setattr("scripts.memory_service.reindex_markdown", fail_once)

    with pytest.raises(RuntimeError, match="injected reindex failure"):
        svc.remember({
            "type": "project_state", "summary": "must not survive reindex failure",
            "supersedes": [old["memory_id"]],
        })

    after = {path.name: path.read_text() for path in root.glob("*.md")}
    assert calls == 2
    assert after == before
    assert svc.get(old["memory_id"])["status"] == "active"
