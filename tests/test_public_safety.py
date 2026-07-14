from pathlib import Path

from scripts.check_public_safety import inspect_tree


def test_public_safety_accepts_generic_examples(tmp_path):
    (tmp_path / "profile.json").write_text(
        '{"knowledge_root":"~/Documents/DNA-Memory-Vault"}', encoding="utf-8"
    )

    assert inspect_tree(tmp_path) == []


def test_public_safety_rejects_private_paths_and_tokens(tmp_path):
    private_root = "/" + "Users/private-person/Desktop/private-vault"
    token = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    (tmp_path / "config.txt").write_text(
        "root={}\ntoken={}".format(private_root, token), encoding="utf-8"
    )

    findings = inspect_tree(tmp_path)

    assert {finding[1] for finding in findings} == {
        "private identifier", "OpenAI-style token"
    }
