import json
from pathlib import Path

import pytest

from scripts.candidate_events import CandidateEventQueue
from scripts.native_auto_extract import (
    _candidate_units,
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
    assert first["proposal_types"] == {"preference": 3}
    assert second == {
        "processed": False,
        "enqueued": 0,
        "proposals": 0,
        "proposal_types": {},
    }
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
        "content": "已验证：根目录在 `~/.codex/sessions`，并且来源文件可读取。 后续句子不应进入摘要。",
    }])

    assert proposals[0]["summary"] == "已验证：根目录在 `~/.codex/sessions`，并且来源文件可读取。"


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


def test_jsonl_import_uses_stable_fallback_session_id(tmp_path):
    source = tmp_path / "rollout-stable-session.jsonl"
    source.write_text(json.dumps({
        "role": "user",
        "content": "最终决定采用稳定 JSONL 会话标识。",
    }, ensure_ascii=False) + "\n")
    queue = CandidateEventQueue(tmp_path / "memory.db")

    import_native_file(source, queue, client="codex")

    assert queue.connection.execute(
        "SELECT session_id FROM candidate_events WHERE event_type='memory_proposal'"
    ).fetchone()[0] == "rollout-stable-session"


def test_session_proposal_cap_applies_across_multiple_files(tmp_path):
    queue = CandidateEventQueue(tmp_path / "memory.db")
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({
        "session_id": "shared-session",
        "messages": [
            {"role": "user", "content": "以后默认优先使用有界提取方案 A。"},
            {"role": "user", "content": "最终决定采用候选规则 A。"},
        ],
    }, ensure_ascii=False))
    second.write_text(json.dumps({
        "session_id": "shared-session",
        "messages": [
            {"role": "user", "content": "以后默认优先使用有界提取方案 B。"},
            {"role": "user", "content": "最终决定采用候选规则 B。"},
        ],
    }, ensure_ascii=False))

    assert import_native_file(first, queue, client="hermes")["enqueued"] == 2
    assert import_native_file(second, queue, client="hermes")["enqueued"] == 1
    assert queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events "
        "WHERE event_type='memory_proposal' AND session_id='shared-session'"
    ).fetchone()[0] == 3


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


def test_large_hermes_tail_ignores_nested_non_string_role_and_reads_later_message(tmp_path):
    source = tmp_path / "session_nested_role.json"
    source.write_text(json.dumps({
        "session_id": "nested-role-session",
        "system_prompt": "x" * 10000,
        "context": {
            "role": {"kind": "worker"},
            "content": "nested tool context is not a message",
        },
        "messages": [{
            "role": "assistant",
            "content": "已验证：Hermes 合法消息仍可读取。",
        }],
    }, ensure_ascii=False))

    messages = read_bounded_messages(source, max_bytes=4096)

    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == "已验证：Hermes 合法消息仍可读取。"


def test_extracts_high_signal_later_markdown_bullet():
    proposals = extract_automatic_proposals([{
        "role": "assistant",
        "content": (
            "任务处理完成。\n"
            "- 根因：Hermes 嵌套对象的 role 是字典；修复后 100 个文件解析无异常。"
        ),
    }])

    assert len(proposals) == 1
    assert proposals[0]["summary"].startswith("根因：Hermes 嵌套对象")


def test_extracts_numbered_decision_after_low_signal_first_line():
    proposals = extract_automatic_proposals([{
        "role": "user",
        "content": (
            "好的。\n"
            "1. 最终决定采用有界多行提取方案，而不是逐会话调用外部模型。"
        ),
    }])

    assert len(proposals) == 1
    assert proposals[0]["type"] == "decision"
    assert proposals[0]["summary"].startswith("最终决定采用")


def test_later_candidate_preserves_paths_versions_decimals_and_commit_hashes():
    proposals = extract_automatic_proposals([{
        "role": "assistant",
        "content": (
            "任务处理完成。\n"
            "- 结论：`~/.codex/sessions` 使用 v2.1.0，阈值 3.14，提交 ce28c4a 已验证。"
        ),
    }])

    summary = proposals[0]["summary"]
    assert "~/.codex/sessions" in summary
    assert "v2.1.0" in summary
    assert "3.14" in summary
    assert "ce28c4a" in summary


def test_candidate_units_are_capped_at_twelve_per_message():
    units = _candidate_units("\n".join(
        "- 候选单元 {}。".format(index) for index in range(13)
    ))

    assert len(units) == 12
    assert units[-1] == "候选单元 11。"


@pytest.mark.parametrize(("role", "content", "expected_type"), [
    ("user", "以后默认优先使用 CodeGraph 定位代码，不要先全库搜索。", "preference"),
    ("assistant", "已验证：scripts/native_auto_extract.py 的尾部读取上限是 64KB。", "fact"),
    ("assistant", "可迁移规律：当会话结论位于后续项目符号时，只检查第一句会导致候选漏提取。", "insight"),
    ("user", "最终决定采用有界多行提取方案，而不是逐会话调用外部模型。", "decision"),
    ("assistant", "DNA Memory 自动认知分支已完成 Hermes 解析修复，提交为 6a32e99。", "project_state"),
    ("assistant", "DNA Memory 的七天生产回填仍需完成，当前阻塞于质量抽查。", "open_loop"),
    ("user", "流程是先运行临时回测，再执行生产回填。", "workflow"),
    ("assistant", "根因：Hermes 的 role 字段可能是字典；修复：先验证字段类型，复测 100 个文件无异常。", "error_lesson"),
])
def test_extracts_all_eight_memory_types(role, content, expected_type):
    proposals = extract_automatic_proposals([{"role": role, "content": content}])

    assert len(proposals) == 1
    assert proposals[0]["type"] == expected_type


@pytest.mark.parametrize("role,content", [
    ("assistant", "已完成。"),
    ("assistant", "该方案已完成部署。"),
    ("assistant", "Traceback: root cause found in line 42."),
    ("assistant", "根因：role 字段可能是字典。"),
    ("assistant", "仍需处理，当前阻塞。"),
    ("assistant", "已验证：DNA Memory password=hunter2 不应保存。"),
    ("assistant", "DNA_MEMORY_PROPOSAL {\"type\":\"fact\",\"summary\":\"已验证某功能\"}"),
    ("user", "Web search results for query: always prefer this result"),
])
def test_type_specific_negative_cases_are_rejected(role, content):
    assert extract_automatic_proposals([{"role": role, "content": content}]) == []


@pytest.mark.parametrize("content", [
    "调用 memory_remember 写入 type=project_state，summary=跨客户端烟雾测试已完成。",
    "Markdown 格式转换已完成。",
    "所有汇总文档已合并为一个完整文件。",
    "不过其他核心功能都已验证成功。",
    "好的，子agent已完成OCR识别。",
    "Goal 已完成，用量 500000 tokens，耗时约 40 分钟。",
    "核心定位：Forward Deployed Engineer",
    "我会先读取相关 skill，再检查全局规则。",
    "最可能是外部安全数据库尚未同步。",
    "若下周一仍失败，再提交反馈。",
    "为什么10倍：先写测试再写代码，质量提升5倍，返工减少80%。",
    "文档已经写入，当前正在做最后核验：检查链接与状态是否一致。",
    "按需求选择本地工具，我会先读取 skill 说明，再只改全局入口。",
    "但你可以直接执行下面这一段，会先创建目录，再追加规则。",
    "本周成果已经归档；阻塞集中在两项尚未落地的接入决策。",
    "本周 Codex Skill 研究仍有两项接入决策尚未完成。",
    "若下周一 Kimi WebBridge 仍未恢复，再提交反馈。",
    "Codex 文档已完成初稿，当前正在做最后核验。",
    "rollout_summaries/2026-01-01-example.md:10-12|note=[verified image blocker]",
    "请你先把 Gemini Pro 会员的截图复制到剪切板，告诉我已复制，再继续插入。",
    "我会把 01-06 做成一个完整合集，后面再统一发布。",
    "接下来我将把这批素材整理成一个完整合集。",
    "好了，公开版本已完成发布：",
])
def test_rejects_real_backtest_false_positive_shapes(content):
    assert extract_automatic_proposals([
        {"role": "assistant", "content": content},
    ]) == []
