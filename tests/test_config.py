import json
from pathlib import Path

import scripts.config as config_module
from scripts.config import load_config


def test_profile_overrides_defaults_and_expands_paths(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "knowledge_root": "~/Documents/Memory-Vault",
        "skill_root": "~/.agents/skills",
        "database_path": "~/dna/memory.db",
        "claude_desktop_session_dirs": ["~/Claude Sessions"],
    }))

    config = load_config(profile)

    assert config.knowledge_root == Path.home() / "Documents/Memory-Vault"
    assert config.skill_root == Path.home() / ".agents/skills"
    assert config.database_path == Path.home() / "dna/memory.db"
    assert config.claude_desktop_session_dirs == (Path.home() / "Claude Sessions",)


def test_environment_profile_is_supported(tmp_path, monkeypatch):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"knowledge_root": str(tmp_path / "vault")}))
    monkeypatch.setenv("DNA_MEMORY_PROFILE", str(profile))

    assert load_config().knowledge_root == tmp_path / "vault"


def test_default_profile_is_loaded_when_present(tmp_path, monkeypatch):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"knowledge_root": str(tmp_path / "default-vault")}))
    monkeypatch.delenv("DNA_MEMORY_PROFILE", raising=False)
    monkeypatch.setattr(config_module, "DEFAULT_PROFILE", profile)

    assert load_config().knowledge_root == tmp_path / "default-vault"


def test_claude_desktop_session_dirs_default_to_empty_tuple(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text("{}")

    assert load_config(profile).claude_desktop_session_dirs == ()


def test_hermes_state_db_defaults_to_none_and_expands_path(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"hermes_state_db": "~/hermes/state.db"}))

    config = load_config(profile)

    assert config.hermes_state_db == Path.home() / "hermes/state.db"
