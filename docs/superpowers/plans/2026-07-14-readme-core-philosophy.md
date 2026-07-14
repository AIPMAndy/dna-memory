# DNA Memory README Core Philosophy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore DNA Memory's biomimetically inspired cognitive-memory philosophy in the Chinese and English README files without overstating the implemented system.

**Architecture:** Add a first-screen philosophy section to each README between the existing introduction and safety boundaries. The section maps the brand claim to current primitives: bounded collection, candidate extraction, importance/confidence/feedback ranking, eight durable memory types, recall, and explicit supersession.

**Tech Stack:** Markdown, Python documentation safety checker, pytest, GitHub Actions

---

### Task 1: Add the Chinese core philosophy

**Files:**
- Modify: `README.md:19`

- [ ] **Step 1: Insert the approved philosophy section**

After the paragraph ending with “验证后的关键结论。”, insert:

```markdown
## 核心理念：从对话数据到可复用认知

> **DNA Memory 不把“保存对话”视为“形成记忆”。** 它受人类大脑记忆形成
> 机制启发，把跨客户端的大量对话视为原始感知输入，通过信号提取、重要性与
> 置信度加权、认知分型、验证结晶、召回反馈和新旧认知替代，持续把数据抽象为
> 可复用认知。

它不是另一个无限增长的聊天数据库。原始会话只是形成认知的材料；只有经过筛选、
验证并值得在未来任务中复用的结论，才会进入长期记忆真源。

```text
大量原始对话
  -> 有界采集与信号提取
  -> 重要性、置信度与使用反馈加权
  -> 认知分型
  -> 验证后结晶为长期认知
  -> 按当前任务召回
  -> useful / misleading 反馈与 supersedes 演化
```

当前工程实现将长期认知分为四组、八种类型：

| 认知模型 | 记忆类型 | 用途 |
|---|---|---|
| 个体倾向 | `preference` | 稳定偏好与协作习惯 |
| 事实与洞察 | `fact`, `insight` | 已验证事实与从事实中抽象出的认识 |
| 决策与状态 | `decision`, `project_state`, `open_loop` | 决策理由、当前状态和待闭环事项 |
| 程序与经验 | `workflow`, `error_lesson` | 可复用流程和经过验证的失败经验 |

这里的仿生学是设计启发，不是对人脑的完整复刻。DNA Memory 的价值不取决于
保存了多少对话，而取决于形成了多少高质量认知，以及这些认知是否在后续决策中
被准确召回和有效复用。
```

- [ ] **Step 2: Verify the Chinese positioning is present**

Run:

```bash
rg -n "## 核心理念：从对话数据到可复用认知|把数据抽象为|当前工程实现将长期认知分为四组、八种类型" README.md
```

Expected: three matches in the new first-screen section.

### Task 2: Add the equivalent English philosophy

**Files:**
- Modify: `README_EN.md:20`

- [ ] **Step 1: Insert the equivalent English section**

After the paragraph ending with “verified reusable conclusions.”, insert:

```markdown
## Core philosophy: from conversation data to reusable cognition

> **DNA Memory does not treat storing conversations as forming memories.** It is
> a biomimetically inspired cognitive memory system. Cross-client conversations
> are raw perceptual input; bounded collection, signal extraction, importance and
> confidence weighting, cognitive classification, verification, recall feedback,
> and explicit replacement progressively abstract that data into reusable
> cognition.

It is not another indefinitely growing chat database. Native conversations are
source material; only conclusions that have been filtered, verified, and are
worth reusing in future work become durable memory.

```text
raw conversations
  -> bounded collection and signal extraction
  -> importance, confidence, and usage-feedback weighting
  -> cognitive classification
  -> verified crystallization into durable cognition
  -> task-focused recall
  -> useful / misleading feedback and supersedes evolution
```

The current implementation organizes durable cognition into four groups and
eight memory types:

| Cognitive model | Memory types | Purpose |
|---|---|---|
| Individual tendencies | `preference` | Stable preferences and collaboration habits |
| Facts and insights | `fact`, `insight` | Verified facts and knowledge abstracted from them |
| Decisions and state | `decision`, `project_state`, `open_loop` | Rationale, current state, and unresolved work |
| Procedures and experience | `workflow`, `error_lesson` | Reusable workflows and verified lessons from failure |

Biomimetics is a design inspiration here, not a claim to replicate the human
brain. DNA Memory's value is not how many conversations it stores, but how much
high-quality cognition it forms and whether that cognition is accurately
recalled and effectively reused in later decisions.
```

- [ ] **Step 2: Verify the English positioning is present**

Run:

```bash
rg -n "## Core philosophy: from conversation data to reusable cognition|abstract that data into|four groups and" README_EN.md
```

Expected: three matches in the new first-screen section.

### Task 3: Validate and publish the documentation change

**Files:**
- Verify: `README.md`
- Verify: `README_EN.md`
- Verify: `docs/superpowers/specs/2026-07-14-readme-core-philosophy-design.md`

- [ ] **Step 1: Check terminology against implemented memory types**

Run:

```bash
python3 - <<'PY'
from scripts.markdown_memory import SUPPORTED_TYPES

expected = {
    "preference", "decision", "fact", "insight", "workflow",
    "error_lesson", "project_state", "open_loop",
}
assert SUPPORTED_TYPES == expected
print("README memory types match implementation")
PY
```

Expected: `README memory types match implementation`.

- [ ] **Step 2: Run the complete verification chain**

Run:

```bash
python3 -m pytest -q
python3 -m compileall -q dna.py dna scripts tests
python3 scripts/check_public_safety.py
git diff --check
```

Expected: 108 tests pass; compileall, public safety, and diff checks exit 0.

- [ ] **Step 3: Commit the README implementation**

```bash
git add README.md README_EN.md
GIT_COMMITTER_NAME="DNA Memory Contributors" \
GIT_COMMITTER_EMAIL="noreply@users.noreply.github.com" \
git commit --author="DNA Memory Contributors <noreply@users.noreply.github.com>" \
  -m "docs: restore DNA Memory core philosophy"
```

Expected: one documentation commit with sanitized author and committer metadata.

- [ ] **Step 4: Push, open a pull request, and verify GitHub Actions**

```bash
git push -u origin codex/readme-core-philosophy
gh pr create --repo AIPMAndy/dna-memory \
  --base main \
  --head codex/readme-core-philosophy \
  --title "docs: restore DNA Memory core philosophy" \
  --body "Restore the biomimetically inspired cognitive-memory philosophy in the Chinese and English README files, mapped to the current implementation and safety boundaries."
PR_NUMBER=$(gh pr view --repo AIPMAndy/dna-memory --json number --jq .number)
gh pr checks --watch --fail-fast "$PR_NUMBER" --repo AIPMAndy/dna-memory
```

Expected: the PR is mergeable and all required checks pass.

- [ ] **Step 5: Merge and verify the public main branch**

```bash
PR_NUMBER=$(gh pr view --repo AIPMAndy/dna-memory --json number --jq .number)
gh pr merge "$PR_NUMBER" --repo AIPMAndy/dna-memory --squash --delete-branch
gh pr view "$PR_NUMBER" --repo AIPMAndy/dna-memory --json state,mergedAt,mergeCommit
```

Expected: state is `MERGED`; the public `main` README files contain the new philosophy sections.
