# DNA Memory Value and Recall Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正 DNA Memory 的时间窗口、backlog 和客户端采用率指标，并让共享 Memory Loop Skill 明确要求 Claude、Codex 与 Hermes 在历史相关任务前执行有界召回。

**Architecture:** 在 `scripts/memory_value.py` 内增加独立的时间规范化、backlog 分类和客户端采用率聚合函数，保持数据库只读且不迁移已有记录。行为侧复用现有 `dna skills sync` 单一真源分发机制，只强化已有 `dna-memory-loop` 的触发契约；本机部署继续使用受管的 `andy-memory-loop` 名称。

**Tech Stack:** Python 3 标准库、SQLite、PyYAML、pytest、Agent Skills、MCP、GitHub CLI。

---

## 文件边界

- Modify: `scripts/memory_value.py`：时间解析、窗口过滤、backlog 分类和客户端采用率指标。
- Modify: `tests/test_memory_value.py`：真实时间格式、异常时间、backlog 分类、召回命中和占比测试。
- Modify: `skills/dna-memory-loop/SKILL.md`：公开通用 Skill 的强制触发边界。
- Modify: `tests/test_bundled_skills.py`：固定主动召回契约。
- Modify: `docs/skill-management.md`：说明公开模板、本机真源和三端分发关系。
- Modify: `docs/mcp-and-client-adapters.md`：记录新的 `memory value` 输出字段和验收命令。
- Modify: `README.md`、`README_EN.md`：更新价值指标摘要和主动召回用法。
- Deploy only, not committed: 用户级 Claude/Hermes/Codex 指令与共享 Skill 真源。

### Task 1: 兼容真实时间格式

**Files:**
- Modify: `tests/test_memory_value.py`
- Modify: `scripts/memory_value.py`

- [ ] **Step 1: 写入真实格式的失败测试**

在 `tests/test_memory_value.py` 增加：

```python
def test_memory_value_windows_accept_iso_offsets_and_unix_seconds(tmp_path):
    cfg = config(tmp_path)
    store = UnifiedMemoryStore(cfg.database_path)
    rows = [
        ("iso-basic", "2026-07-10T12:00:00+0800"),
        ("iso-colon", "2026-07-10T12:00:00+08:00"),
        ("sqlite", "2026-07-10 04:00:00"),
        ("unix", 1783656000),
        ("old", "2026-05-01T12:00:00+0800"),
        ("invalid", "not-a-time"),
    ]
    store.connection.executemany(
        "INSERT INTO memory_index "
        "(memory_id,type,status,summary,content_hash,clients,created_at,updated_at,source_kind) "
        "VALUES (?, 'fact', 'active', ?, ?, '[\"codex\"]', ?, ?, 'markdown')",
        [(name, name, name, created_at, created_at) for name, created_at in rows],
    )
    store.connection.commit()
    store.close()

    payload = memory_value(cfg, now="2026-07-11T12:00:00+0800")

    assert payload["all_time"]["new_memories"] == 6
    assert payload["windows"]["7d"]["new_memories"] == 4
```

- [ ] **Step 2: 运行测试并确认旧实现失败**

Run:

```bash
python3 -m pytest tests/test_memory_value.py::test_memory_value_windows_accept_iso_offsets_and_unix_seconds -q
```

Expected: FAIL，旧 SQL `datetime()` 无法把 `+0800` 和 Unix 秒正确计入窗口。

- [ ] **Step 3: 实现最小时间规范化**

在 `scripts/memory_value.py` 中用 Python 标准库替代 `_window_clause`：

```python
from datetime import datetime, timedelta, timezone
import re


OFFSET_WITHOUT_COLON = re.compile(r"([+-]\d{2})(\d{2})$")


def _parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.replace(".", "", 1).isdigit():
            return datetime.fromtimestamp(float(text), timezone.utc)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        text = OFFSET_WITHOUT_COLON.sub(r"\1:\2", text)
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _in_window(value, days, now):
    if days is None:
        return True
    created_at = _parse_timestamp(value)
    current = _parse_timestamp(now)
    if created_at is None or current is None:
        return False
    return current - timedelta(days=days) <= created_at <= current
```

把 `_metrics` 的三个聚合查询改为读取必要字段后用 `_in_window` 过滤。全量统计保留不可解析时间，7 天和 30 天窗口排除不可解析时间。

- [ ] **Step 4: 运行时间与现有价值测试**

Run:

```bash
python3 -m pytest tests/test_memory_value.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交时间兼容修复**

```bash
git add scripts/memory_value.py tests/test_memory_value.py
git commit -m "fix: normalize memory value timestamps"
```

### Task 2: 拆分 backlog 口径

**Files:**
- Modify: `tests/test_memory_value.py`
- Modify: `scripts/memory_value.py`

- [ ] **Step 1: 写入 backlog 分类失败测试**

增加一个独立测试，向 `candidate_events` 写入以下 pending 类型：

```python
def test_memory_value_classifies_pending_events(tmp_path):
    cfg = config(tmp_path)
    queue = CandidateEventQueue(cfg.database_path)
    event_types = [
        "memory_proposal", "session_updated", "session_meta", "turn_context",
        "SessionStart", "Stop", "SessionEnd", "session_closed", "task_complete",
    ]
    for index, event_type in enumerate(event_types):
        queue.enqueue({
            "event_id": "event-{}".format(index),
            "client": "codex",
            "event_type": event_type,
        })
    queue.connection.execute(
        "UPDATE candidate_events SET created_at='2026-07-08 12:00:00'"
    )
    queue.connection.execute(
        "UPDATE candidate_events SET created_at='2026-07-09 12:00:00' "
        "WHERE event_type='memory_proposal'"
    )
    queue.connection.commit()
    queue.connection.close()

    backlog = memory_value(cfg, now="2026-07-11 12:00:00")["backlog"]

    assert backlog == {
        "reviewable_proposals": 1,
        "provenance_events": 3,
        "lifecycle_events": 4,
        "other_pending": 1,
        "total_pending": 9,
        "pending": 9,
        "oldest_pending_at": "2026-07-08 12:00:00",
        "oldest_reviewable_at": "2026-07-09 12:00:00",
    }
```

- [ ] **Step 2: 运行测试并确认字段缺失**

Run:

```bash
python3 -m pytest tests/test_memory_value.py::test_memory_value_classifies_pending_events -q
```

Expected: FAIL，当前 `backlog` 只有 `pending` 和 `oldest_pending_at`。

- [ ] **Step 3: 实现显式事件分类**

在 `scripts/memory_value.py` 增加：

```python
PROVENANCE_EVENT_TYPES = frozenset((
    "session_updated", "session_meta", "turn_context",
))
LIFECYCLE_EVENT_TYPES = frozenset((
    "SessionStart", "Stop", "SessionEnd", "session_closed",
))


def _empty_backlog():
    return {
        "reviewable_proposals": 0,
        "provenance_events": 0,
        "lifecycle_events": 0,
        "other_pending": 0,
        "total_pending": 0,
        "pending": 0,
        "oldest_pending_at": None,
        "oldest_reviewable_at": None,
    }


def _backlog(connection):
    result = _empty_backlog()
    rows = connection.execute(
        "SELECT event_type, created_at FROM candidate_events WHERE status='pending'"
    ).fetchall()
    reviewable_times = []
    pending_times = []
    for event_type, created_at in rows:
        pending_times.append(created_at)
        if event_type == "memory_proposal":
            result["reviewable_proposals"] += 1
            reviewable_times.append(created_at)
        elif event_type in PROVENANCE_EVENT_TYPES:
            result["provenance_events"] += 1
        elif event_type in LIFECYCLE_EVENT_TYPES:
            result["lifecycle_events"] += 1
        else:
            result["other_pending"] += 1
    result["total_pending"] = len(rows)
    result["pending"] = len(rows)
    result["oldest_pending_at"] = min(pending_times) if pending_times else None
    result["oldest_reviewable_at"] = min(reviewable_times) if reviewable_times else None
    return result
```

让无数据库路径和无表路径都返回 `_empty_backlog()`。

- [ ] **Step 4: 更新旧断言并运行测试**

Run:

```bash
python3 -m pytest tests/test_memory_value.py -q
```

Expected: PASS，兼容字段 `pending == total_pending`。

- [ ] **Step 5: 提交 backlog 分类**

```bash
git add scripts/memory_value.py tests/test_memory_value.py
git commit -m "feat: classify memory candidate backlog"
```

### Task 3: 增加客户端召回命中与占比

**Files:**
- Modify: `tests/test_memory_value.py`
- Modify: `scripts/memory_value.py`

- [ ] **Step 1: 写入客户端采用率失败断言**

在现有聚合测试中加入：

```python
assert payload["clients"]["codex"]["recall_hits"] == 1
assert payload["clients"]["claude"]["recall_hits"] == 0
assert payload["clients"]["hermes"]["recall_hits"] == 1
assert payload["clients"]["codex"]["recall_share"] == 1 / 3
assert payload["clients"]["claude"]["recall_share"] == 1 / 3
assert payload["clients"]["hermes"]["recall_share"] == 1 / 3
```

在无数据库测试中加入：

```python
assert payload["clients"]["codex"]["recall_hits"] == 0
assert payload["clients"]["codex"]["recall_share"] == 0.0
```

- [ ] **Step 2: 运行测试并确认字段缺失**

Run:

```bash
python3 -m pytest tests/test_memory_value.py -q
```

Expected: FAIL with `KeyError: 'recall_hits'`。

- [ ] **Step 3: 实现客户端采用率字段**

修改字段和聚合查询：

```python
CLIENT_FIELDS = (
    "candidate_events", "recall_attempts", "recall_hits",
    "returned_memories", "useful", "misleading", "new_memories",
    "recall_share",
)
```

```python
for client, attempts, hits, returned in connection.execute(
    "SELECT client, COUNT(*), "
    "COALESCE(SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END), 0), "
    "COALESCE(SUM(result_count), 0) "
    "FROM memory_recall_events GROUP BY client"
):
    add(client, "recall_attempts", attempts)
    add(client, "recall_hits", hits)
    add(client, "returned_memories", returned)
```

聚合完成后计算：

```python
total_attempts = sum(item["recall_attempts"] for item in clients.values())
for item in clients.values():
    item["recall_share"] = (
        item["recall_attempts"] / total_attempts if total_attempts else 0.0
    )
```

`add()` 只处理计数；`recall_share` 直接赋浮点值。

- [ ] **Step 4: 运行价值测试**

Run:

```bash
python3 -m pytest tests/test_memory_value.py tests/test_memory_cli.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交客户端采用率**

```bash
git add scripts/memory_value.py tests/test_memory_value.py
git commit -m "feat: report client recall adoption"
```

### Task 4: 强化主动召回 Skill 契约

**Files:**
- Modify: `tests/test_bundled_skills.py`
- Modify: `skills/dna-memory-loop/SKILL.md`
- Modify: `docs/skill-management.md`

- [ ] **Step 1: 写入强制触发契约失败测试**

在 `tests/test_bundled_skills.py` 增加：

```python
def test_memory_loop_requires_recall_for_history_dependent_work():
    body = (ROOT / "skills/dna-memory-loop/SKILL.md").read_text(encoding="utf-8")

    assert "MUST recall before relying on history" in body
    for trigger in ("prior", "continue", "last time", "same plan"):
        assert trigger in body
    assert "one to four distinctive terms" in body
    assert "simple, self-contained" in body
    assert "Memory failure must not block" in body
```

- [ ] **Step 2: 运行测试并确认强制文案缺失**

Run:

```bash
python3 -m pytest tests/test_bundled_skills.py::test_memory_loop_requires_recall_for_history_dependent_work -q
```

Expected: FAIL，因为现有 Skill 描述了流程但没有明确 MUST 边界和触发词。

- [ ] **Step 3: 最小修改 Skill**

在 `## Before substantive work` 开头增加：

```markdown
You MUST recall before relying on history. Treat a task as history-dependent
when it refers to prior work, asks to continue, mentions last time or the same
plan, names an existing project or path, or depends on a durable preference,
known error, workflow, project state, or open loop.
```

保留现有 1 至 4 个关键词、5 条记忆、2,000 tokens、当前证据优先和 degraded mode 限制。

- [ ] **Step 4: 更新 Skill 管理文档**

在 `docs/skill-management.md` 明确：公开仓库模板名是 `dna-memory-loop`；个人部署可在共享真源使用自定义受管名称；三端目标必须是指向同一共享目录的链接，不能手工维护三个副本。

- [ ] **Step 5: 运行 Skill 与同步测试**

Run:

```bash
python3 -m pytest tests/test_bundled_skills.py tests/test_skill_manager.py tests/test_skills_cli.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交 Skill 契约**

```bash
git add skills/dna-memory-loop/SKILL.md tests/test_bundled_skills.py docs/skill-management.md
git commit -m "feat: require bounded recall for substantive tasks"
```

### Task 5: 更新公开用法与输出说明

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `docs/mcp-and-client-adapters.md`

- [ ] **Step 1: 更新中文用法**

记录以下稳定接口：

```text
backlog.reviewable_proposals
backlog.provenance_events
backlog.lifecycle_events
backlog.other_pending
backlog.total_pending
clients.codex.recall_hits / clients.claude.recall_hits / clients.hermes.recall_hits
clients.codex.recall_share / clients.claude.recall_share / clients.hermes.recall_share
```

明确 `pending` 只是 `total_pending` 的兼容别名，不能解释为待审记忆数量。

- [ ] **Step 2: 同步英文说明**

英文 README 只翻译产品行为，不写入本机路径、真实客户端计数或会话标识。

- [ ] **Step 3: 文档脱敏扫描**

Run:

```bash
rg -n '/Users/|mem_[0-9a-f]{8}|session[_-]?id.{0,20}[0-9a-f]{8}' \
  README.md README_EN.md docs skills scripts tests
```

Expected: 无本次新增的个人绝对路径、真实记忆 ID 或真实会话 ID。

- [ ] **Step 4: 提交文档**

```bash
git add README.md README_EN.md docs/mcp-and-client-adapters.md
git commit -m "docs: explain memory value adoption metrics"
```

### Task 6: 全量验证、公开发布与本机部署

**Files:**
- Verify: repository test suite
- Deploy: live DNA Memory installation and user-level shared Skill

- [ ] **Step 1: 运行全量测试和静态检查**

Run:

```bash
git diff --check origin/main...HEAD
python3 -m pytest -q
```

Expected: `155` 个基线测试加新增测试全部 PASS，`git diff --check` 无输出。

- [ ] **Step 2: 用临时数据库验证 CLI JSON**

Run:

```bash
python3 dna.py memory value --json
```

Expected: JSON 含新 backlog 和客户端字段，不输出记忆摘要、数据库路径或凭证。

- [ ] **Step 3: 推送公开分支并创建 PR**

```bash
git push -u origin codex/memory-value-recall-adoption
PR_URL=$(gh pr create \
  --repo AIPMAndy/dna-memory \
  --base main \
  --head codex/memory-value-recall-adoption \
  --title "Fix memory value metrics and strengthen active recall" \
  --body $'## Summary\n- normalize real-world memory timestamps\n- split reviewable backlog from provenance events\n- report per-client recall adoption\n- strengthen bounded recall guidance\n\n## Verification\n- python3 -m pytest -q')
PR_NUMBER=${PR_URL##*/}
```

Expected: PR 指向公开仓库，不包含本机路径、真实计数、真实记忆或会话数据。

- [ ] **Step 4: 检查 CI 并合并**

```bash
gh pr checks --repo AIPMAndy/dna-memory "$PR_NUMBER" --watch
gh pr merge --repo AIPMAndy/dna-memory "$PR_NUMBER" --squash --delete-branch
```

Expected: 必需检查通过，PR squash merge 到 `main`。

- [ ] **Step 5: 部署到 live 目录且保留现有差异**

先列出 live 目录已有修改，再只更新本功能涉及的文件。不得 reset、checkout 或覆盖无关的 README/importer 差异。

```bash
DNA_MEMORY_LIVE="$HOME/.cc-switch/skills/dna-memory"
DNA_MEMORY_DB="$HOME/.local/share/dna-memory/memory.db"
git -C "$DNA_MEMORY_LIVE" status --short
git -C "$DNA_MEMORY_LIVE" diff -- scripts/memory_value.py tests/test_memory_value.py
```

只应用本功能涉及的文件：

```bash
git diff 320b751..HEAD -- \
  scripts/memory_value.py tests/test_memory_value.py \
  skills/dna-memory-loop/SKILL.md tests/test_bundled_skills.py \
  docs/skill-management.md docs/mcp-and-client-adapters.md \
  README.md README_EN.md \
  | git -C "$DNA_MEMORY_LIVE" apply --3way
```

若命令报告冲突，停止自动应用并读取冲突文件，使用 `apply_patch` 把本功能块合入 live 内容；不得回退用户已有修改。

- [ ] **Step 6: 强化本机单一 Skill 真源并同步三端**

在用户级共享 `andy-memory-loop/SKILL.md` 写入与公开 Skill 等价的 MUST 触发段，然后运行：

```bash
python3 dna.py skills sync --apply --json
python3 dna.py skills doctor --json
```

Expected: Codex、Claude、Hermes 的 `andy-memory-loop` 均指向同一共享真源，无 conflict 或 broken link。

- [ ] **Step 7: 运行 live 价值核对**

```bash
python3 dna.py memory value --json
sqlite3 -readonly "$DNA_MEMORY_DB" \
  "SELECT event_type, COUNT(*) FROM candidate_events WHERE status='pending' GROUP BY event_type ORDER BY event_type;"
```

Expected: 7 天/30 天新增数不再因 `+0800` 变为零；`reviewable_proposals` 等于 pending 的 `memory_proposal`；分类之和等于 `total_pending`。

- [ ] **Step 8: 新会话验证 Claude Code 主动召回**

先记录 `memory_recall_events` 最新行号，再运行一个明确依赖历史、但不直接命令调用 MCP 的新会话：

```bash
claude -p --output-format json \
  "继续之前的 DNA Memory 价值统计工作。先恢复相关历史，再只报告你使用了哪些记忆。"
```

Expected: 会话实际调用 `memory_recall`，数据库新增 `client` 属于 Claude 的召回事件；只输出结果不算通过。

- [ ] **Step 9: 新会话验证 Hermes 及子 Agent 可发现性**

```bash
hermes skills list --source local --enabled-only | rg 'andy-memory-loop'
hermes -z "继续之前的 DNA Memory 价值统计工作。先恢复相关历史，再只报告你使用了哪些记忆。"
```

Expected: Hermes 能发现 Skill，实际调用 `memory_recall`，数据库新增 Hermes 召回事件。随后用 Hermes 的委派能力启动一个子 Agent 执行同类历史任务，并确认子 Agent 也产生 Hermes 召回事件。

- [ ] **Step 10: 故障降级验收**

用仅本次进程有效的无效 MCP 配置启动一个新客户端会话，要求完成自包含任务。不得改全局配置。

Expected: 客户端报告一次记忆降级但仍完成主任务，不声称召回成功。

- [ ] **Step 11: 最终状态确认**

```bash
git status --short --branch
python3 -m pytest -q
python3 dna.py memory status --json
```

Expected: 开发 worktree 干净、全量测试通过、live 数据库 `state: ok` 且可写。
