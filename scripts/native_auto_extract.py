#!/usr/bin/env python3
"""Bounded automatic proposal extraction for native client session files."""

import hashlib
import json
import re
from pathlib import Path

from scripts.bounded_proposals import DEFAULT_MAX_PROPOSALS
from scripts.candidate_events import CandidateEventQueue
from scripts.policy import inspect_content

DEFAULT_MAX_BYTES = 64 * 1024
DEFAULT_MAX_MESSAGES = 12
DEFAULT_MAX_UNITS = 12

_USER_RULES = (
    ("preference", re.compile(r"(?:记住|以后.{0,80}(?:不要|必须|优先|默认)|默认(?:使用|采用|不要)|不要再|必须始终|优先使用|我偏好|remember|by default|always|never)")),
    ("decision", re.compile(r"(?:我(?:们)?决定|决定采用|最终决定|确定使用|采用.{0,60}方案|选择.{0,60}而不是|we decided|final decision|adopt.{0,60}approach)")),
    ("workflow", re.compile(r"(?:(?:以后|必须)先.{0,80}再|流程是|步骤是|first.{0,80}then)")),
)
_FACT_EVIDENCE = re.compile(
    r"(?:已验证[：:]?|验证结果[：:]|测试证明|verified[：:]?|confirmed[：:]?|tests? pass(?:ed)?[：:]?)",
    re.IGNORECASE,
)
_PROJECT_STATE = re.compile(
    r"(?:已完成|已部署|已发布|已合并|已修复|仍未完成|尚未完成|"
    r"completed|published|merged|fixed|(?:has been|is|was) deployed)",
    re.IGNORECASE,
)
_OPEN_LOOP = re.compile(
    r"(?:仍需|尚未|仍未|未完成|阻塞(?:于)?|下一步(?:是|需|要)?|pending|blocked)",
    re.IGNORECASE,
)
_INSIGHT = re.compile(
    r"(?:可迁移规律|通用规律|规律[：:]|核心约束[：:]|模式是|"
    r"(?:因为|由于).{2,160}(?:导致|所以|因此)|会导致|意味着)",
    re.IGNORECASE,
)
_WORKFLOW = re.compile(
    r"(?:流程是|步骤是|应当先|应该先|先.{2,100}再|the workflow|steps are|first.{2,100}then)",
    re.IGNORECASE,
)
_ERROR_CAUSE = re.compile(r"(?:根因[：:]|失败条件[：:]|root cause[：:]?|fails? when)", re.IGNORECASE)
_ERROR_REMEDY = re.compile(
    r"(?:修复(?:后|[：:])|解决[：:]|规避[：:]|改为|复测|验证后|fixed by|avoid(?:ed)? by)",
    re.IGNORECASE,
)
_CONCRETE_SUBJECT = re.compile(
    r"(?:`[^`]+`|[/~][\w./-]+|[A-Za-z][A-Za-z0-9_.-]{2,}|"
    r"项目|系统|功能|文件|脚本|分支|流程|命令|接口|数据库|会话|候选|回填|发布|"
    r"测试|客户端|规则|字段|解析|记忆|版本|提交)"
)
_TRANSIENT = re.compile(
    r"(?:现在|今天|明天|今晚|待会|下午|上午|本周|下周|if I am|later today)",
    re.IGNORECASE,
)
_MEMORY_ECHO = re.compile(
    r"(?:共找到\s*\d+\s*条记忆|\bID:\s*\d+|内容:\s*|"
    r"^(?:web )?search results? for query:|"
    r"^(?:MEMORY\.md|rollout_summaries/|skills/).*\|note=\[)",
    re.IGNORECASE,
)
_VAGUE_ASSISTANT = re.compile(
    r"^(?:(?:已修复|已完成)(?:并)?(?:重新)?(?:打开|处理|完成)?(?:这|该)?(?:条)?"
    r"(?:对话|任务|问题|内容)(?:串)?[。.]?|I(?:'ve| have) published and verified the live post[.]?)$",
    re.IGNORECASE,
)
_META_MEMORY = re.compile(
    r"(?:人工审查|自动提取|误采集|记忆检索|候选(?:里|中|项)|DNA_MEMORY_PROPOSAL|"
    r"memory_(?:remember|recall|feedback|close_session))",
    re.IGNORECASE,
)
_LOW_SIGNAL_STATUS = re.compile(
    r"(?:publication report|same-day content|最新主题和详情|"
    r"(?:全量|现有|单元)?测试(?:通过|\s*`?\d+ passed)|"
    r"DNA Memory.{0,80}(?:完全可用|验证完成)|记忆总数|MCP 工具)",
    re.IGNORECASE,
)
_VAGUE_REFERENCE = re.compile(
    r"^(?:结论[：:]?\s*)?(?:这|它|该(?:方向|方案|系统|功能|问题))",
    re.IGNORECASE,
)
_CONVERSATIONAL_STATUS = re.compile(
    r"^(?:你说得对[，,]?我应该|已创建文件\s*\[)",
    re.IGNORECASE,
)
_CHECKLIST_STATUS = re.compile(r"^(?:✅|☑|✔)")
_LOG_OUTPUT = re.compile(r"^(?:Traceback|\$\s|(?:DEBUG|INFO|WARN|ERROR)\b)", re.IGNORECASE)
_FUTURE_NARRATION = re.compile(
    r"(?:^|[，,：:]\s*)(?:我(?:会|将)?先|我会优先|I(?:'ll| will) (?:first|start by))",
    re.IGNORECASE,
)
_UNVERIFIED_SPECULATION = re.compile(r"^(?:最可能|大概率|可能是|推测)", re.IGNORECASE)
_IN_PROGRESS_NARRATION = re.compile(
    r"(?:当前)?正在(?:做|进行|检查|核验|处理)",
    re.IGNORECASE,
)
_COMMAND_PREFACE = re.compile(
    r"^(?:但)?你可以直接执行下面",
    re.IGNORECASE,
)
_ACTION_HANDOFF = re.compile(
    r"^(?:请你先|告诉我(?:已|已经)|复制到剪切板|复制到剪贴板|"
    r"再继续(?:插入|执行)|等你(?:确认|回复)|等待你)",
    re.IGNORECASE,
)
_PLANNING_NARRATION = re.compile(
    r"^(?:我会把|我将把|接下来我(?:将|会)|正在(?:把|将|整理|制作|进行))",
    re.IGNORECASE,
)
_UNSUBSTANTIVE_COMPLETION = re.compile(
    r"^(?:好了[，,]?\s*)?公开版本已完成发布[：:]?$",
    re.IGNORECASE,
)
_GENERIC_COMPLETION = re.compile(
    r"^(?:Markdown\s+格式转换|(?:所有|全部).{0,30}(?:文档|文件)|"
    r"(?:不过)?其他.{0,20}功能|好的[，,]?\s*子agent).{0,50}"
    r"(?:已完成|已合并|已验证)",
    re.IGNORECASE,
)
_RESOURCE_STATUS = re.compile(
    r"^Goal\s+已完成.{0,80}(?:tokens?|耗时)",
    re.IGNORECASE,
)
_UNVERIFIED_PROMOTIONAL = re.compile(
    r"(?:为什么\s*\d+\s*倍|提升\s*\d+\s*倍|减少\s*\d+\s*%)",
    re.IGNORECASE,
)

_IMPORTANCE = {
    "preference": 0.8,
    "decision": 0.8,
    "error_lesson": 0.8,
    "insight": 0.75,
    "project_state": 0.75,
    "workflow": 0.75,
    "fact": 0.7,
    "open_loop": 0.7,
}


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(part for item in value if (part := _text(item)))
    if isinstance(value, dict):
        for key in ("text", "content", "message", "output"):
            if key in value:
                text = _text(value[key])
                if text:
                    return text
    return ""


def _record_message(record):
    if not isinstance(record, dict):
        return None
    role = record.get("role")
    role = role if isinstance(role, str) else None
    record_type = record.get("type")
    record_type = record_type if isinstance(record_type, str) else None
    body = record
    if role not in {"user", "assistant"} and record_type in {"user", "assistant"}:
        role = record_type
    if role not in {"user", "assistant"} and record_type == "response_item":
        body = record.get("payload")
        if not isinstance(body, dict):
            return None
        if body.get("type") != "message":
            return None
        role = body.get("role")
        role = role if isinstance(role, str) else None
    if role not in {"user", "assistant"}:
        return None
    content = body.get("content")
    if content is None:
        message = body.get("message")
        content = message.get("content") if isinstance(message, dict) else None
    text = _text(content).strip()
    return {
        "role": role,
        "content": text,
        "project_path": record.get("cwd") or body.get("cwd"),
    } if text else None


def _messages_from_data(data):
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return [item for item in (_record_message(message) for message in data["messages"]) if item]
    if isinstance(data, list):
        return [item for item in (_record_message(record) for record in data) if item]
    return []


def _messages_from_json_tail(raw):
    text = raw.decode("utf-8", errors="ignore")
    decoder = json.JSONDecoder()
    messages = []
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            record, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        item = _record_message(record)
        if item:
            messages.append(item)
    return messages


def _read_tail_bytes(path, max_bytes):
    path = Path(path)
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(max(0, size - int(max_bytes)))
        return handle.read(int(max_bytes)), size


def read_bounded_messages(path, max_bytes=DEFAULT_MAX_BYTES, max_messages=DEFAULT_MAX_MESSAGES):
    """Read only the bounded tail and return user/assistant messages."""
    path = Path(path)
    tail, size = _read_tail_bytes(path, max_bytes)
    if path.suffix.lower() == ".json":
        try:
            return _messages_from_data(json.loads(tail.decode("utf-8")))[:max_messages]
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _messages_from_json_tail(tail)[-max_messages:]
    lines = tail.decode("utf-8", errors="ignore").splitlines()
    if size > len(tail) and lines:
        lines = lines[1:]
    messages = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = _record_message(record)
        if item:
            messages.append(item)
    return messages[-max_messages:]


def _candidate_units(text, max_units=DEFAULT_MAX_UNITS):
    units = []
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = re.sub(r"^(?:[-*+]\s+|\d+[.)、]\s*)", "", line).strip()
        if not line:
            continue
        for part in re.split(r"(?<=[。！？!?])|(?<=\.)\s+", line):
            unit = part.strip()
            if unit:
                units.append(unit[:800].strip())
            if len(units) >= int(max_units):
                return units
    return units


def _has_concrete_subject(text):
    return len(text) >= 12 and not _VAGUE_REFERENCE.search(text) and bool(
        _CONCRETE_SUBJECT.search(text)
    )


def _classify_candidate(role, text):
    if role == "user":
        for memory_type, pattern in _USER_RULES:
            if pattern.search(text):
                return memory_type
        return None
    if role != "assistant" or not _has_concrete_subject(text):
        return None
    if _ERROR_CAUSE.search(text) and _ERROR_REMEDY.search(text):
        return "error_lesson"
    if _OPEN_LOOP.search(text):
        return "open_loop"
    if _PROJECT_STATE.search(text):
        return "project_state"
    if _FACT_EVIDENCE.search(text):
        return "fact"
    if _INSIGHT.search(text):
        return "insight"
    if _WORKFLOW.search(text):
        return "workflow"
    return None


def extract_automatic_proposals(messages, max_proposals=DEFAULT_MAX_PROPOSALS):
    """Extract high-signal short proposals; never return the source transcript."""
    proposals = []
    seen = set()
    for message in messages:
        for text in _candidate_units(message.get("content", "")):
            if (_MEMORY_ECHO.search(text) or _META_MEMORY.search(text)
                    or _LOW_SIGNAL_STATUS.search(text) or _VAGUE_REFERENCE.search(text)
                    or _CONVERSATIONAL_STATUS.search(text)
                    or _CHECKLIST_STATUS.search(text) or _TRANSIENT.search(text)
                    or _LOG_OUTPUT.search(text) or _FUTURE_NARRATION.search(text)
                    or _UNVERIFIED_SPECULATION.search(text)
                    or _IN_PROGRESS_NARRATION.search(text) or _COMMAND_PREFACE.search(text)
                    or _GENERIC_COMPLETION.search(text) or _RESOURCE_STATUS.search(text)
                    or _UNVERIFIED_PROMOTIONAL.search(text)
                    or _ACTION_HANDOFF.search(text) or _PLANNING_NARRATION.search(text)
                    or _UNSUBSTANTIVE_COMPLETION.search(text)
                    or not inspect_content(text).allowed):
                continue
            if message.get("role") == "assistant" and _VAGUE_ASSISTANT.match(text):
                continue
            memory_type = _classify_candidate(message.get("role"), text)
            if memory_type:
                key = re.sub(r"\s+", " ", text).lower()
                if key in seen:
                    continue
                seen.add(key)
                proposals.append({
                    "type": memory_type,
                    "summary": text,
                    "confidence": "high" if message.get("role") == "user" else "medium",
                    "importance": _IMPORTANCE[memory_type],
                })
            if len(proposals) >= max_proposals:
                return proposals[:max_proposals]
    return proposals[:max_proposals]


def _session_id(path, messages):
    if Path(path).suffix == ".json":
        try:
            raw, size = _read_tail_bytes(path, DEFAULT_MAX_BYTES)
            data = json.loads(raw.decode("utf-8")) if size <= len(raw) else {}
            if isinstance(data, dict):
                value = data.get("session_id") or data.get("sessionId") or data.get("cliSessionId")
                if isinstance(value, (str, int)) and str(value).strip():
                    return str(value)
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    if Path(path).suffix == ".jsonl":
        try:
            raw, _ = _read_tail_bytes(path, DEFAULT_MAX_BYTES)
            for line in raw.decode("utf-8", errors="ignore").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload") if isinstance(record, dict) else None
                value = record.get("session_id") or record.get("sessionId") or record.get("cliSessionId")
                if not value and isinstance(payload, dict):
                    value = payload.get("id") or payload.get("session_id")
                if isinstance(value, (str, int)) and str(value).strip():
                    return str(value)
        except OSError:
            pass
    return Path(path).stem


def _project_path(path, messages):
    for message in messages:
        if message.get("project_path"):
            return str(message["project_path"])
    return None


def import_native_file(path, queue, client, max_bytes=DEFAULT_MAX_BYTES, force=False):
    path = Path(path).expanduser().resolve()
    stat = path.stat()
    source_ref = str(path)
    checkpoint_ref = "native-auto:{}:{}".format(client, source_ref)
    tail, _ = _read_tail_bytes(path, max_bytes)
    digest = hashlib.sha256(tail).hexdigest()
    checkpoint = queue.get_checkpoint(checkpoint_ref)
    if not force and checkpoint and checkpoint[2] == digest:
        return {
            "processed": False,
            "enqueued": 0,
            "proposals": 0,
            "proposal_types": {},
        }
    messages = read_bounded_messages(path, max_bytes=max_bytes)
    proposals = extract_automatic_proposals(messages)
    proposal_types = {}
    for proposal in proposals:
        memory_type = proposal["type"]
        proposal_types[memory_type] = proposal_types.get(memory_type, 0) + 1
    session_id = _session_id(path, messages)
    project_path = _project_path(path, messages)
    enqueued = 0
    existing_proposals = queue.connection.execute(
        "SELECT COUNT(*) FROM candidate_events "
        "WHERE client=? AND session_id=? AND event_type='memory_proposal'",
        (client, session_id),
    ).fetchone()[0]
    remaining = max(0, DEFAULT_MAX_PROPOSALS - existing_proposals)
    for index, proposal in enumerate(proposals[:remaining]):
        normalized = re.sub(r"\s+", " ", proposal["summary"]).strip().lower()
        event_hash = hashlib.sha256(
            (client + "|" + str(session_id) + "|" + normalized).encode()
        ).hexdigest()
        source_hash = hashlib.sha256(
            (source_ref + "|" + digest + "|" + str(index) + "|" + normalized).encode()
        ).hexdigest()
        if queue.enqueue({
            "event_id": "auto_proposal_" + event_hash[:24],
            "client": client,
            "event_type": "memory_proposal",
            "session_id": session_id,
            "project_path": project_path,
            "source_ref": source_ref + "#proposal=" + str(index),
            "source_hash": source_hash,
            "excerpt": proposal["summary"],
            "memory_type": proposal["type"],
            "confidence": proposal["confidence"],
            "importance": proposal["importance"],
        }):
            enqueued += 1
    if not proposals:
        pointer_hash = hashlib.sha256((source_ref + digest).encode()).hexdigest()
        if queue.enqueue({
            "event_id": "auto_session_" + pointer_hash[:24],
            "client": client,
            "event_type": "session_updated",
            "session_id": session_id,
            "project_path": project_path,
            "source_ref": source_ref,
            "source_hash": digest,
        }):
            enqueued += 1
    queue.update_checkpoint(checkpoint_ref, stat.st_ino, stat.st_size, digest)
    return {
        "processed": True,
        "enqueued": enqueued,
        "proposals": len(proposals),
        "proposal_types": proposal_types,
    }
