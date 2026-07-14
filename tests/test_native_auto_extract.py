import json
from pathlib import Path

from scripts.candidate_events import CandidateEventQueue
from scripts.native_auto_extract import (
    extract_automatic_proposals,
    import_native_file,
    read_bounded_messages,
)


def test_extracts_bounded_preference_and_verified_conclusion_without_transcript():
    messages = [
        {"role": "user", "content": "记住，以后先验证再写入长期记忆，不要保存完整对话。"},
        {"role": "assistant", "content": "已验证：候选必须经过 daily 结晶，普通来源只保存指针。"},
    ]

    proposals = extract_automatic_proposals(messages)

    assert len(proposals) == 2
    assert proposals[0]["type"] == "preference"
    assert "完整对话" in proposals[0]["summary"]
    assert proposals[1]["type"] in {"fact", "workflow"}
    assert all(len(item["summary"]) <= 800 for item in proposals)


def test_native_jsonl_import_reads_only_tail_and_emits_pointer_or_proposals(tmp_path, monkeypatch):
    source = tmp_path / "session.jsonl"
    records = [
        {"type": "user", "message": {"role": "user", "content": "private old prompt"}},
        {"type": "assistant", "message": {"role": "assistant", "content": "old tool output"}},
        {"type": "user", "message": {"role": "user", "content": "决定采用候选队列，不保存完整 transcript。"}},
        {"type": "assistant", "cwd": "/tmp/project", "message": {"role": "assistant", "content": "已验证候选队列可通过 daily 结晶。"}},
    ]
    source.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records))
    queue = CandidateEventQueue(tmp_path / "memory.db")
    monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(
        AssertionError("native import must not read the whole file")
    ))

    result = import_native_file(source, queue, client="claude-desktop", max_bytes=512)

    assert result["processed"] is True
    rows = queue.connection.execute(
        "SELECT event_type, excerpt FROM candidate_events ORDER BY event_id"
    ).fetchall()
    assert rows
    assert any(row[0] == "memory_proposal" for row in rows)
    assert all(row[1] is None or len(row[1]) <= 800 for row in rows)
    assert "private old prompt" not in json.dumps([tuple(row) for row in rows])
    assert queue.connection.execute(
        "SELECT project_path FROM candidate_events WHERE event_type='memory_proposal' LIMIT 1"
    ).fetchone()[0] == "/tmp/project"


def test_native_import_is_idempotent_and_caps_three_proposals(tmp_path):
    source = tmp_path / "session.jsonl"
    source.write_text("\n".join(
        json.dumps({"role": "user", "content": "以后必须记住决定 %s" % index}, ensure_ascii=False)
        for index in range(5)
    ) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")

    first = import_native_file(source, queue, client="hermes")
    second = import_native_file(source, queue, client="hermes")

    assert first["enqueued"] == 3
    assert second == {"processed": False, "enqueued": 0, "proposals": 0}
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchone()[0] == 3
    assert queue.get_checkpoint("native-auto:hermes:" + str(source.resolve())) is not None


def test_rejects_transient_decisions_memory_echoes_and_vague_status():
    messages = [
        {"role": "user", "content": "现在下午3点了，我决定待会如果不困就出去。"},
        {"role": "user", "content": "共找到 11 条记忆：ID: 9 内容: 永远优先使用某工具。"},
        {"role": "assistant", "content": "已修复并重新打开这条对话串。"},
        {"role": "assistant", "content": "人工审查发现候选里有过于模糊的“已修复”，需要加入自动提取过滤。"},
        {"role": "assistant", "content": "I've published and verified the live post."},
        {"role": "user", "content": "Web search results for query: \"FreeFound never miss automated updates\""},
    ]

    assert extract_automatic_proposals(messages) == []


def test_rejects_multiline_logs_release_status_and_old_memory_self_report():
    messages = [
        {"role": "assistant", "content": "让我统计一下今天的实际工作时间：\n\n客观结论：今天工作时间确实很短。"},
        {"role": "assistant", "content": "Everything needed for the publication report is verified: same-day content was already live."},
        {"role": "assistant", "content": "全量测试通过，README 现在是双语结构。"},
        {"role": "assistant", "content": "结论：它现在能证明方向可行，但不能证明客户会买单。"},
        {"role": "assistant", "content": "DNA Memory 本机完全可用验证完成，记忆总数 72,113 条。"},
        {"role": "assistant", "content": "两个核心迁移任务已完成：\n✅ 飞书知识库已迁移\n✅ 增量更新已验证正常"},
        {"role": "assistant", "content": "你说得对，我应该先检查更多记忆文件，而不是反复问你。"},
        {"role": "assistant", "content": "已创建文件 [修图任务思考.md](修图任务思考.md)，记录了核心结论："},
    ]

    assert extract_automatic_proposals(messages) == []


def test_sentence_does_not_split_inside_dot_path():
    proposals = extract_automatic_proposals([{
        "role": "assistant",
        "content": "结论：根目录在 `~/.codex/sessions`，并且来源文件可读取。 后续句子不应进入摘要。",
    }])

    assert proposals[0]["summary"] == "结论：根目录在 `~/.codex/sessions`，并且来源文件可读取。"


def test_same_session_summary_deduplicates_across_mirrored_files(tmp_path):
    queue = CandidateEventQueue(tmp_path / "memory.db")
    content = json.dumps({
        "session_id": "same-session",
        "messages": [{"role": "user", "content": "记住，以后不要保存完整对话。"}],
    }, ensure_ascii=False)
    first = tmp_path / "one.json"
    second = tmp_path / "two.json"
    first.write_text(content)
    second.write_text(content)

    assert import_native_file(first, queue, client="claude-desktop")["enqueued"] == 1
    assert import_native_file(second, queue, client="claude-desktop")["enqueued"] == 0


def test_large_hermes_json_reads_complete_messages_from_bounded_tail(tmp_path, monkeypatch):
    source = tmp_path / "session_large.json"
    source.write_text(json.dumps({
        "session_id": "large-session",
        "system_prompt": "x" * 200000,
        "messages": [
            {"role": "user", "content": "old private message"},
            {"role": "assistant", "content": "已验证：Hermes 大型 JSON 只解析有界尾部。"},
        ],
        "message_count": 2,
    }, ensure_ascii=False))
    monkeypatch.setattr(Path, "read_text", lambda self, *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("bounded reader must not read the whole JSON file")
    ))

    messages = read_bounded_messages(source, max_bytes=4096)

    assert messages[-1]["role"] == "assistant"
    assert "有界尾部" in messages[-1]["content"]
    assert sum(len(message["content"]) for message in messages) < 4096
