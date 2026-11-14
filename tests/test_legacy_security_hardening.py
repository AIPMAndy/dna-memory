"""Regression coverage for SkillsCat-reported legacy entry points."""

import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    file = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location("audit_" + file.stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_advanced_recall_cli_redacts_content_by_default(monkeypatch, capsys):
    mod = load_script("advanced_recall.py")
    secret = "PRIVATE_MEMO_SENSITIVE_CONTENT"
    monkeypatch.setattr(mod, "advanced_recall", lambda **kwargs: [
        {"id": 1, "type": "fact", "content": secret, "weight": 0.7, "tags": "PRIVATE_TAG_SENSITIVE_CONTENT"}
    ])
    monkeypatch.setattr(sys, "argv", ["advanced_recall.py", "query"])
    mod.main()
    captured = capsys.readouterr().out
    assert secret not in captured
    assert "PRIVATE_TAG_SENSITIVE_CONTENT" not in captured
    assert "--show-content" in captured

    monkeypatch.setattr(sys, "argv", ["advanced_recall.py", "query", "--show-content"])
    mod.main()
    revealed = capsys.readouterr().out
    assert secret in revealed
    assert "PRIVATE_TAG_SENSITIVE_CONTENT" in revealed


def test_pending_review_does_not_promote_or_disclose(monkeypatch, tmp_path, capsys):
    mod = load_script("reflect_pending.py")
    pending = tmp_path / "pending.json"
    payload = '[{"content":"PRIVATE_MEMO_SENSITIVE_CONTENT","confidence":0.9,"type":"fact"}]'
    pending.write_text(payload, encoding="utf-8")
    pending.chmod(0o600)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    assert mod.review_pending(pending) == 1
    output = capsys.readouterr().out
    assert "PRIVATE_MEMO_SENSITIVE_CONTENT" not in output
    assert pending.read_text(encoding="utf-8") == payload
    assert "No proposals were promoted" in output


def test_pending_review_refuses_public_file_and_symlink(tmp_path):
    mod = load_script("reflect_pending.py")
    pending = tmp_path / "pending.json"
    pending.write_text("[]", encoding="utf-8")
    pending.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        mod.review_pending(pending)

    pending.chmod(0o600)
    link = tmp_path / "link.json"
    link.symlink_to(pending)
    with pytest.raises(ValueError, match="symbolic link"):
        mod.review_pending(link)


def test_daemon_does_not_log_memory_content(monkeypatch, tmp_path):
    mod = load_script("dna_memory_daemon.py")
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout="PRIVATE_MEMO_SENSITIVE_CONTENT",
            stderr="SECRET_ERROR_TEXT",
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    log = tmp_path / "private.log"
    assert mod.run_action("reflect", log, None, 12) == 0
    assert seen["command"] == [sys.executable, str(mod.EVOLVE_SCRIPT), "reflect"]
    assert seen["kwargs"]["shell"] is False
    assert seen["kwargs"]["stdin"] == mod.subprocess.DEVNULL
    text = log.read_text(encoding="utf-8")
    assert "PRIVATE_MEMO_SENSITIVE_CONTENT" not in text
    assert "SECRET_ERROR_TEXT" not in text
    assert stat.S_IMODE(log.stat().st_mode) == 0o600
    with pytest.raises(ValueError, match="Unsupported"):
        mod.run_action("arbitrary", log, None, 12)


def test_daemon_refuses_symlinks_for_pid_and_log(tmp_path):
    mod = load_script("dna_memory_daemon.py")
    target = tmp_path / "target"
    target.write_text("KEEP", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        mod.write_pid_private(link, 123)
    with pytest.raises(ValueError, match="symlink"):
        mod.log_line(link, "status")
    assert target.read_text(encoding="utf-8") == "KEEP"

    pid = tmp_path / "daemon.pid"
    mod.write_pid_private(pid, 123)
    assert pid.read_text(encoding="utf-8") == "123"
    assert stat.S_IMODE(pid.stat().st_mode) == 0o600
