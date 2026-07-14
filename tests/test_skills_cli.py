import json

from scripts.skills_cli import main


def test_sync_defaults_to_dry_run_and_apply_creates_only_missing_links(tmp_path, capsys):
    shared = tmp_path / "shared"
    source = shared / "one"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: one\n---\n")
    codex = tmp_path / "codex"
    registry = tmp_path / "skills.json"
    registry.write_text(json.dumps({"skills": {"one": {"targets": ["codex"]}}}))
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "knowledge_root": str(tmp_path / "vault"),
        "database_path": str(tmp_path / "memory.db"),
        "skill_root": str(shared),
        "skill_registry": str(registry),
        "platform_skill_roots": {"codex": str(codex)},
    }))

    assert main(["--profile", str(profile), "sync", "--json"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert dry["changed"] == 0
    assert (codex / "one").exists() is False

    assert main(["--profile", str(profile), "sync", "--apply", "--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["changed"] == 1
    assert (codex / "one").resolve() == source.resolve()
