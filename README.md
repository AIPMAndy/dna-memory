<div align="center">

# DNA Memory

**面向 Codex、Claude Code、Claude Desktop、Hermes 与 Obsidian 的本地优先统一记忆层**

[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/)

[English](./README_EN.md) | 简体中文 | [快速上手](./QUICKSTART.md)

</div>

DNA Memory 把一个 Markdown/Obsidian 目录作为长期记忆真源，把 SQLite
作为可删除、可重建的索引。多个 AI 客户端通过同一个 MCP 服务召回、写入和反馈，
不再各自维护互相冲突的长期记忆副本。

它不会把“保存所有聊天记录”等同于“形成记忆”。完整会话仍由原客户端保管；
DNA Memory 只保存有界来源指针、经过审查的提案，以及验证后的关键结论。

## 核心边界

- Markdown 是长期真源，SQLite 是索引和遥测层。
- `memory_remember` 写入的是短小、可复用结论，不是 transcript。
- 自动导入默认只保存 session ID、路径、哈希、偏移和计数。
- 自动提炼每个会话最多产生 3 条候选，每条最多 800 字符。
- 凭证、私钥、常见 token 和疑似敏感内容会被拒绝。
- 普通 Claude Desktop 云端聊天没有稳定本地正文来源时，只能显式 MCP 写回。
- 任何客户端的记忆故障都不应阻塞主任务。

## 架构

```text
Codex / Claude / Hermes
          |
          | stdio MCP
          v
  memory_recall / remember / feedback
          |
          +--> Markdown vault       <- durable source of truth
          |
          +--> SQLite index         <- rebuildable search + telemetry
          |
          +--> bounded candidates   <- pointers and reviewable proposals

Native client histories remain in their original stores.
```

## 安装

```bash
git clone https://github.com/AIPMAndy/dna-memory.git \
  "$HOME/.local/share/dna-memory/app"
cd "$HOME/.local/share/dna-memory/app"

python3 -m venv "$HOME/.local/share/dna-memory/mcp-venv"
"$HOME/.local/share/dna-memory/mcp-venv/bin/pip" install \
  -r requirements-mcp.txt

mkdir -p "$HOME/.config/dna-memory" "$HOME/Documents/DNA-Memory-Vault/Memory"
cp docs/profiles/profile.example.json \
  "$HOME/.config/dna-memory/profile.json"
```

按需编辑仓库外的 profile：

```json
{
  "knowledge_root": "~/Documents/DNA-Memory-Vault",
  "database_path": "~/.local/share/dna-memory/memory.db",
  "managed_memory_dir": "Memory",
  "skill_root": "~/.agents/skills",
  "skill_registry": "~/.config/dna-memory/skills.json",
  "platform_skill_roots": {
    "codex": "~/.codex/skills",
    "claude": "~/.claude/skills",
    "hermes": "~/.hermes/skills"
  }
}
```

```bash
export DNA_MEMORY_PROFILE="$HOME/.config/dna-memory/profile.json"
python3 dna.py memory status --json
python3 dna.py memory reindex --json
```

## 接入三个客户端

以下命令让 Codex、Claude Code 和 Hermes 指向同一个 profile 与 MCP 服务：

```bash
ROOT="$HOME/.local/share/dna-memory/app"
PYTHON="$HOME/.local/share/dna-memory/mcp-venv/bin/python"
PROFILE="$HOME/.config/dna-memory/profile.json"

codex mcp add dna-memory \
  --env "DNA_MEMORY_PROFILE=$PROFILE" \
  -- "$PYTHON" "$ROOT/scripts/memory_mcp.py"

claude mcp add --scope user dna-memory \
  -e "DNA_MEMORY_PROFILE=$PROFILE" \
  -- "$PYTHON" "$ROOT/scripts/memory_mcp.py"

hermes mcp add dna-memory \
  --command "$PYTHON" \
  --env "DNA_MEMORY_PROFILE=$PROFILE" \
  --args "$ROOT/scripts/memory_mcp.py"
```

验收时不要只看配置文件：

```bash
codex mcp get dna-memory
claude mcp get dna-memory
hermes mcp test dna-memory
```

Claude Desktop 使用 `mcpServers` 配置，且 JSON 中必须是绝对路径。安全迁移、
备份和回滚见 [客户端接入文档](docs/mcp-and-client-adapters.md)。

## MCP 工具

| 工具 | 用途 |
|---|---|
| `memory_recall` | 用 1 至 4 个独立关键词召回活跃记忆 |
| `memory_get` | 按稳定 ID 获取单条记忆和替代关系 |
| `memory_remember` | 写入验证后的长期结论 |
| `memory_feedback` | 标记召回结果 `useful` 或 `misleading` |
| `memory_close_session` | 保存有界会话来源指针 |
| `memory_status` | 查看真源和索引状态 |
| `memory_reindex` | 从 Markdown 重建 SQLite 索引 |

推荐将 [dna-memory-loop](skills/dna-memory-loop/SKILL.md) 分发到各客户端。
它规定了同一套行为：任务前召回、确实使用后反馈、验证后才写回。

## 日常操作

```bash
# 真源、容量与索引状态
python3 dna.py memory status --json

# 客户端来源、自动捕获和 MCP 边界
python3 dna.py memory coverage --json

# 召回、命中、反馈、写回和积压指标
python3 dna.py memory value --json

# 从 Markdown 重建索引
python3 dna.py memory reindex --json

# 结晶安全提案、清理候选、备份、完整性检查
python3 dna.py memory maintain daily --json
python3 dna.py memory maintain weekly --json
python3 dna.py memory maintain monthly --json
```

当新证据明确使旧结论失效时，调用 `memory_remember` 并显式传入旧 ID：

```json
{
  "type": "project_state",
  "summary": "客户端接入已经通过真实召回与写回验收。",
  "supersedes": ["mem_old_unverified"]
}
```

旧 Markdown 会保留并改为 `superseded`；默认召回只返回 active 结论。
系统不会仅按项目或类型猜测冲突。

## 自动导入与提炼

可按需要运行：

```bash
python3 scripts/import_codex_rollouts.py
python3 scripts/import_claudian_sessions.py
python3 scripts/import_claude_desktop_sessions.py
python3 scripts/import_hermes_sessions.py
python3 scripts/import_native_history.py
```

导入器使用检查点和幂等事件 ID。普通事件只保存指针；只有显式
`DNA_MEMORY_PROPOSAL {JSON}` 或通过有界信号提取的短结论才进入候选队列，
并且仍需经过 daily 维护的类型、敏感信息、容量和去重检查。

这意味着“扫描到了会话”不等于“已经形成长期认知”。衡量系统价值时应同时看：

1. 自动捕获覆盖率。
2. 长期记忆写入数量。
3. 召回命中率与 `useful` 反馈。
4. 是否减少重复说明和重复错误。

## 跨客户端 Skill 管理

共享 Skill 真源与记忆真源分开管理。注册表只声明 DNA Memory 有权分发的
Skill，注册表外的客户端专属目录不会被删除或覆盖。

```bash
cp assets/skills.example.json "$HOME/.config/dna-memory/skills.json"
python3 dna.py skills inventory --json
python3 dna.py skills doctor --json
python3 dna.py skills sync --json
python3 dna.py skills sync --apply --json
```

`sync` 默认 dry-run，`--apply` 只创建缺失符号链接。详见
[Skill 管理](docs/skill-management.md)。

## 隐私与公开安全

仓库不包含真实 profile、数据库、会话、记忆 JSON、个人 Skill 或内部部署记录。
发布前运行：

```bash
python3 scripts/check_public_safety.py
```

本地 profile、备份、SQLite 和 Markdown vault 不应位于 Git 仓库内。
如果曾误提交凭证，仅删除文件不够，还必须撤销凭证并清理 Git 历史。

## 开发验证

```bash
python3 -m pytest -q
python3 -m compileall -q dna.py dna scripts tests
python3 scripts/check_public_safety.py
git diff --check
```

## License

[MIT](LICENSE)
