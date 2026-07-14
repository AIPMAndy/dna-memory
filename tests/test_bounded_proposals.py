import json

from scripts.bounded_proposals import extract_proposals


def test_extracts_only_explicit_bounded_proposals():
    text = """
    普通结论不应自动入库。
    DNA_MEMORY_PROPOSAL {"type":"decision","summary":"统一记忆以 Obsidian Markdown 为真源","confidence":"high","importance":0.9}
    DNA_MEMORY_PROPOSAL {"type":"fact","summary":"第二条","confidence":"medium"}
    """

    proposals = extract_proposals(text)

    assert proposals == [
        {
            "type": "decision",
            "summary": "统一记忆以 Obsidian Markdown 为真源",
            "confidence": "high",
            "importance": 0.9,
        },
        {"type": "fact", "summary": "第二条", "confidence": "medium"},
    ]


def test_rejects_sensitive_invalid_and_unbounded_proposals():
    secret = "DNA_MEMORY_PROPOSAL " + json.dumps({
        "type": "fact", "summary": "password: hunter2"
    })
    long_summary = "DNA_MEMORY_PROPOSAL " + json.dumps({
        "type": "fact", "summary": "x" * 801
    })
    invalid = "DNA_MEMORY_PROPOSAL {\"type\":\"unknown\",\"summary\":\"x\"}"
    invalid_confidence = "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"x\",\"confidence\":\"certain\"}"
    invalid_importance = "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"x\",\"importance\":2}"

    assert extract_proposals("\n".join((
        secret, long_summary, invalid, invalid_confidence, invalid_importance,
    ))) == []


def test_caps_proposals_and_reads_only_tail(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text("private old content\n" + "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"tail\"}\n")

    from scripts.bounded_proposals import read_tail_proposals

    assert read_tail_proposals(path, max_bytes=200, max_proposals=1) == [
        {"type": "fact", "summary": "tail"}
    ]
