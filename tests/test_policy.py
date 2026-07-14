import pytest

from scripts.policy import capacity_status, inspect_content


@pytest.mark.parametrize("content", [
    "sk-" + "abcdefghijklmnopqrstuvwxyz123456",
    "-----BEGIN " + "PRIVATE KEY-----",
    "password=secret123",
    "A" * 6000,
])
def test_sensitive_content_is_rejected(content):
    result = inspect_content(content)
    assert result.allowed is False
    assert result.reason


def test_capacity_hard_limit_blocks_writes(tmp_path):
    db = tmp_path / "memory.db"
    db.write_bytes(b"12")

    status = capacity_status(db, warning_bytes=1, hard_bytes=2)

    assert status.state == "blocked"
    assert status.writable is False
