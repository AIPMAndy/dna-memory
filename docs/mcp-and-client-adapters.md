# 统一 Memory MCP 与客户端接入

本页描述 DNA Memory 当前的跨客户端用法、隐私边界和运维方式。所有路径均为
通用示例；真实 profile、vault、数据库和会话目录必须留在仓库外。

## 数据边界

- `memory_remember` 执行类型、敏感内容和容量检查后，原子写入受管 Markdown。
- `memory_reindex` 从 Markdown 重建 SQLite；Markdown 删除后重建会同步删除索引。
- 原生会话导入器默认只保存会话 ID、项目路径、来源指针、偏移、哈希和计数。
- 完整 transcript、base64、工具大输出、reasoning 和凭证不会复制到候选队列。
- 只有安全的 `memory_proposal` 才允许在 daily 维护中结晶为长期记忆。
- 召回遥测保存查询 SHA-256、客户端、会话 ID、结果数和时间，不保存查询正文。

## MCP 工具

| 工具 | 说明 |
|---|---|
| `memory_recall(query, limit, client, session_id)` | 召回 active 记忆 |
| `memory_get(memory_id)` | 获取单条记忆及替代关系 |
| `memory_remember(...)` | 写入验证后的结论 |
| `memory_feedback(memory_id, outcome, ...)` | 记录 useful/misleading |
| `memory_close_session(...)` | 记录有界来源指针 |
| `memory_status()` | 查看真源和索引 |
| `memory_reindex()` | 从 Markdown 重建索引 |

`memory_recall` 支持多词匹配，并结合命中词数、反馈、置信度、重要性和更新时间
排序。默认最多 20 条；客户端行为 Skill 应进一步限制上下文注入量。

### 替代过时结论

```json
{
  "type": "project_state",
  "summary": "部署已经通过真实跨端召回验收。",
  "supersedes": ["mem_old_waiting", "mem_old_unverified"]
}
```

所有旧 ID 必须是受管目录内的 active Markdown 记忆。成功后新记忆为 active，
旧记忆标记为 superseded；默认召回不再返回旧结论，`memory_get` 仍可读取历史。
不要按项目或类型自动推断替代关系。

## 独立运行时

```bash
git clone https://github.com/AIPMAndy/dna-memory.git \
  "$HOME/.local/share/dna-memory/app"
cd "$HOME/.local/share/dna-memory/app"

python3 -m venv "$HOME/.local/share/dna-memory/mcp-venv"
"$HOME/.local/share/dna-memory/mcp-venv/bin/pip" install \
  -r requirements-mcp.txt

mkdir -p "$HOME/.config/dna-memory"
cp docs/profiles/profile.example.json \
  "$HOME/.config/dna-memory/profile.json"
```

建议使用独立 venv，避免改变系统 Python 或客户端依赖。

## Codex

```bash
codex mcp add dna-memory \
  --env "DNA_MEMORY_PROFILE=$HOME/.config/dna-memory/profile.json" \
  -- "$HOME/.local/share/dna-memory/mcp-venv/bin/python" \
  "$HOME/.local/share/dna-memory/app/scripts/memory_mcp.py"

codex mcp get dna-memory
```

Codex 没有统一可靠的会话结束 hook，因此可周期运行增量导入器：

```bash
python3 "$HOME/.local/share/dna-memory/app/scripts/import_codex_rollouts.py"
```

它按文件 inode、字节偏移和首行指纹建立检查点，只保存 rollout 级来源指针。
有限尾部窗口只接受 assistant 输出中的显式提案，不复制逐条消息。

## Claude Code

```bash
claude mcp add --scope user dna-memory \
  -e "DNA_MEMORY_PROFILE=$HOME/.config/dna-memory/profile.json" \
  -- "$HOME/.local/share/dna-memory/mcp-venv/bin/python" \
  "$HOME/.local/share/dna-memory/app/scripts/memory_mcp.py"

claude mcp get dna-memory
```

可把以下非阻塞脚本追加到现有 `SessionStart`、`Stop` 和 `SessionEnd` hooks，
不要覆盖用户已有 hooks：

```bash
python3 "$HOME/.local/share/dna-memory/app/scripts/client_event_hook.py"
```

`Stop` 优先读取官方 `last_assistant_message`，旧版本才回退到 transcript 尾部
64KB。普通生命周期事件只保存指针。

## Claude Desktop

Claude Desktop 与 Claude Code 的 MCP 配置相互独立。`mcpServers` 必须使用绝对
路径，以下占位符需要替换：

```json
{
  "mcpServers": {
    "dna-memory": {
      "command": "/ABSOLUTE/PATH/mcp-venv/bin/python",
      "args": ["/ABSOLUTE/PATH/dna-memory/scripts/memory_mcp.py"],
      "env": {
        "DNA_MEMORY_PROFILE": "/ABSOLUTE/PATH/profile.json"
      }
    }
  }
}
```

已有配置应先 dry-run 迁移：

```bash
python3 scripts/configure_claude_desktop.py \
  --config "$CLAUDE_DESKTOP_CONFIG" \
  --python "$DNA_MEMORY_PYTHON" \
  --server "$DNA_MEMORY_ROOT/scripts/memory_mcp.py" \
  --profile "$DNA_MEMORY_PROFILE" \
  --backup-dir "$HOME/.local/share/dna-memory/migration-backups"
```

确认 `would_add` 或 `would_replace` 后追加 `--apply`。配置器会原子备份与替换，
不会删除旧数据；遇到未知自定义 `dna-memory` 服务时会停止。回滚：

```bash
python3 scripts/configure_claude_desktop.py \
  --config "$CLAUDE_DESKTOP_CONFIG" \
  --rollback "$CONFIG_BACKUP"
```

普通云端聊天没有已验证的稳定本地 transcript 时，覆盖报告会标记
`explicit-mcp-writeback`。不能把“配置了 MCP”描述为“自动捕获了所有云端聊天”。

## Hermes

```bash
hermes mcp add dna-memory \
  --command "$HOME/.local/share/dna-memory/mcp-venv/bin/python" \
  --env "DNA_MEMORY_PROFILE=$HOME/.config/dna-memory/profile.json" \
  --args "$HOME/.local/share/dna-memory/app/scripts/memory_mcp.py"

hermes mcp list
hermes mcp test dna-memory
```

命名 profile 需要在对应 profile 中重复配置，不能只检查默认 profile。
`import_hermes_sessions.py` 通过 SQLite 只读 URI 读取 Hermes 状态库，只保存 session
元数据、消息数量和最大 message ID。为了发现显式提案，每个会话只检查最近 8 条
assistant 消息，不保存未命中标记的正文、reasoning 或工具参数。

## 原生历史自动提炼

```bash
python3 scripts/import_claudian_sessions.py
python3 scripts/import_claude_desktop_sessions.py
python3 scripts/import_hermes_sessions.py
python3 scripts/import_native_history.py
```

普通历史扫描使用客户端白名单、尾部 64KB、最多 12 条消息和每端文件预算。
`request_dump`、工具结果、配置文件和账号数据不作为聊天正文。检查点独立且幂等；
重复运行时未变化来源应为 `enqueued=0`。

来源指针由 `max_candidate_events` 限制，默认 10,000 条待处理普通事件。达到上限
时拒绝新增普通指针，但不阻塞客户端主任务。不要用扩大上限代替维护。

## 维护与价值

```bash
python3 dna.py memory status --json
python3 dna.py memory coverage --json
python3 dna.py memory value --json
python3 dna.py memory maintain daily --json
python3 dna.py memory maintain weekly --json
python3 dna.py memory maintain monthly --json
```

- daily：结晶安全提案，压缩旧指针，清理过期终态事件。
- weekly：daily + SQLite 在线备份、有限轮换和 `VACUUM`。
- monthly：weekly + `PRAGMA integrity_check` 和 Markdown 重建核对。

自动化可使用 macOS LaunchAgent、cron 或其他调度器。建议使用通用 label：

```text
io.dna-memory.native-history-import
io.dna-memory.hermes-import
io.dna-memory.daily
io.dna-memory.weekly
io.dna-memory.monthly
```

日志只保留紧凑计数、备份路径和完整性结果，不输出摘要或正文。

## Skill 管理

```bash
python3 dna.py skills inventory --json
python3 dna.py skills doctor --json
python3 dna.py skills sync --json
python3 dna.py skills sync --apply --json
```

`skill_root` 是共享 Skill 真源，注册表决定可分发范围。注册表外的客户端专属
Skill 永不自动删除或覆盖。详见 [skill-management.md](skill-management.md)。

## 验收与回滚

部署后至少完成：

1. `memory_status` 成功。
2. 客户端实际列出 7 个 MCP 工具。
3. 一端 `remember` 后同端 `recall` 命中同一 ID。
4. 另一端能召回该 ID。
5. `memory_feedback(useful)` 成功。
6. SQLite `integrity_check` 为 `ok`。

回滚时移除客户端 MCP 配置和新增 hook。不要删除 Markdown 真源或共享 Skill
真源；SQLite 可从 Markdown 重建。禁用导入调度不会删除原生会话。
