import json

from scripts.skill_manager import build_sync_plan, inventory


def skill(root, name, text):
    path = root / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(text)
    return path


def layout(tmp_path):
    shared = tmp_path / "shared"
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    shared.mkdir()
    codex.mkdir()
    claude.mkdir()
    source = skill(shared, "shared-ok", "---\nname: shared-ok\n---\n")
    (codex / "shared-ok").symlink_to(source, target_is_directory=True)
    skill(claude, "shared-ok", "different")
    skill(claude, "claude-only", "platform")
    (codex / "broken-link").symlink_to(tmp_path / "missing", target_is_directory=True)
    registry = {
        "skills": {
            "shared-ok": {"targets": ["codex", "claude"]},
            "missing-target": {"targets": ["codex"]},
        }
    }
    return shared, {"codex": codex, "claude": claude}, registry


def test_inventory_classifies_shared_conflict_platform_and_broken(tmp_path):
    shared, roots, registry = layout(tmp_path)

    findings = inventory(shared, roots, registry)
    states = {(item.name, item.platform): item.state for item in findings}

    assert states[("shared-ok", "codex")] == "shared"
    assert states[("shared-ok", "claude")] == "conflict"
    assert states[("claude-only", "claude")] == "platform"
    assert states[("broken-link", "codex")] == "broken_link"


def test_sync_plan_never_overwrites_conflicts(tmp_path):
    shared, roots, registry = layout(tmp_path)

    plan = build_sync_plan(shared, roots, registry)
    actions = {(item.name, item.platform): item.action for item in plan}

    assert actions[("shared-ok", "codex")] == "ok"
    assert actions[("shared-ok", "claude")] == "blocked_conflict"
    assert actions[("missing-target", "codex")] == "missing_source"
