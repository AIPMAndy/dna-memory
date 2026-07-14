import json

import pytest

from scripts.configure_claude_desktop import configure, rollback


def paths(tmp_path):
    config = tmp_path / "Claude-3p/claude_desktop_config.json"
    config.parent.mkdir()
    legacy = tmp_path / "memory.jsonl"
    legacy.write_text('{"legacy":"keep me"}\n')
    return config, legacy, tmp_path / "backups"


def desired(tmp_path):
    return {
        "python": str(tmp_path / "venv/bin/python"),
        "server": str(tmp_path / "memory_mcp.py"),
        "profile": str(tmp_path / "profile.json"),
    }


def test_dry_run_reports_replacement_without_writes(tmp_path):
    config, legacy, backup_dir = paths(tmp_path)
    original = json.dumps({
        "mcpServers": {
            "dna-memory": {"name": "dna-memory", "command": "mcp-server-memory"},
            "other": {"command": "other-server"},
        }
    }).encode()
    config.write_bytes(original)

    result = configure(
        config, legacy_memory=legacy, backup_dir=backup_dir, apply=False,
        **desired(tmp_path)
    )

    assert result["status"] == "would_replace"
    assert config.read_bytes() == original
    assert not backup_dir.exists()


def test_apply_backs_up_replaces_only_target_and_rollback_is_byte_identical(tmp_path):
    config, legacy, backup_dir = paths(tmp_path)
    original = b'{\n  "mcpServers": {\n    "dna-memory": {"command": "mcp-server-memory"},\n    "other": {"command": "other-server"}\n  }\n}\n'
    config.write_bytes(original)
    legacy_original = legacy.read_bytes()

    result = configure(
        config, legacy_memory=legacy, backup_dir=backup_dir, apply=True,
        stamp="20260712T010203", **desired(tmp_path)
    )

    assert result["status"] == "replaced"
    backup = result["config_backup"]
    assert backup.endswith("claude_desktop_config.json.20260712T010203.bak")
    assert (backup_dir / "claude_desktop_config.json.20260712T010203.bak").read_bytes() == original
    assert (backup_dir / "memory.jsonl.20260712T010203.bak").read_bytes() == legacy_original
    assert legacy.read_bytes() == legacy_original
    payload = json.loads(config.read_text())
    assert payload["mcpServers"]["other"] == {"command": "other-server"}
    assert payload["mcpServers"]["dna-memory"] == {
        "command": desired(tmp_path)["python"],
        "args": [desired(tmp_path)["server"]],
        "env": {"DNA_MEMORY_PROFILE": desired(tmp_path)["profile"]},
    }

    restored = rollback(config, backup)

    assert restored["status"] == "rolled_back"
    assert config.read_bytes() == original


def test_custom_target_requires_explicit_replace_flag(tmp_path):
    config, legacy, backup_dir = paths(tmp_path)
    config.write_text(json.dumps({
        "mcpServers": {"dna-memory": {"command": "/custom/server"}}
    }))

    with pytest.raises(ValueError, match="custom dna-memory server"):
        configure(
            config, legacy_memory=legacy, backup_dir=backup_dir, apply=True,
            **desired(tmp_path)
        )

    assert not backup_dir.exists()


@pytest.mark.parametrize("raw", ["not-json", '{"other": {}}'])
def test_invalid_or_missing_mcp_servers_fails_without_writes(tmp_path, raw):
    config, legacy, backup_dir = paths(tmp_path)
    config.write_text(raw)
    original = config.read_bytes()

    with pytest.raises(ValueError):
        configure(
            config, legacy_memory=legacy, backup_dir=backup_dir, apply=True,
            **desired(tmp_path)
        )

    assert config.read_bytes() == original
    assert not backup_dir.exists()
