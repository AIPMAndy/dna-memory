from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("dna-memory-loop",)


@pytest.mark.parametrize("name", SKILLS)
def test_bundled_skill_has_cross_client_memory_contract(name):
    path = ROOT / "skills" / name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    _, raw, body = text.split("---", 2)
    meta = yaml.safe_load(raw)

    assert meta["name"] == name
    assert meta["description"].startswith("Use when")
    assert "Before substantive work" in body
    assert "After verification" in body
    assert "Memory failure must not block" in body


def test_memory_loop_has_bounded_active_use_gates():
    body = (ROOT / "skills/dna-memory-loop/SKILL.md").read_text(encoding="utf-8")

    assert "one to four distinctive terms" in body
    assert "at most five memories" in body
    assert "memory_feedback" in body
    assert "memory_remember" in body
    assert "Current files" in body
    assert "full transcript" in body
    assert "displayed but not used" in body
    assert "simple, self-contained" in body
    assert "supersedes" in body
    assert "Never infer replacement" in body


def test_memory_loop_requires_recall_for_history_dependent_work():
    body = (ROOT / "skills/dna-memory-loop/SKILL.md").read_text(encoding="utf-8")

    assert "MUST recall before relying on history" in body
    for trigger in ("prior", "continue", "last time", "same plan"):
        assert trigger in body
    assert "one to four distinctive terms" in body
    assert "simple, self-contained" in body
    assert "Memory failure must not block" in body


def test_memory_loop_requires_truthful_client_metadata():
    body = (ROOT / "skills/dna-memory-loop/SKILL.md").read_text(encoding="utf-8")

    assert "client=hermes" in body
    assert "Never invent client or session metadata" in body
    assert "omit session_id" in body
    assert "placeholder" in body
