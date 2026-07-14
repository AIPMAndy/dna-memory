import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_convenience_entry_has_no_install_path_hardcoding():
    text = (ROOT / "dna").read_text(encoding="utf-8")
    assert ".cc-switch/skills/dna-memory" not in text


def test_old_command_help_runs_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "dna.py"), "manage", "--help"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_new_command_help_runs_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "dna.py"), "memory", "--help"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_convenience_entry_forwards_new_namespaces(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "dna"), "skills", "--help"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
