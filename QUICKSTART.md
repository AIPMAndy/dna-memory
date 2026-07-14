# DNA Memory 快速上手

目标：让 Codex、Claude Code 和 Hermes 共用一个本地 Markdown/Obsidian
长期记忆库，并用 SQLite 提供可重建检索。

## 1. 安装

```bash
git clone https://github.com/AIPMAndy/dna-memory.git \
  "$HOME/.local/share/dna-memory/app"
cd "$HOME/.local/share/dna-memory/app"

python3 -m venv "$HOME/.local/share/dna-memory/mcp-venv"
"$HOME/.local/share/dna-memory/mcp-venv/bin/pip" install \
  -r requirements-mcp.txt
```

## 2. 创建仓库外 profile

```bash
mkdir -p "$HOME/.config/dna-memory" "$HOME/Documents/DNA-Memory-Vault/Memory"
cp docs/profiles/profile.example.json \
  "$HOME/.config/dna-memory/profile.json"
export DNA_MEMORY_PROFILE="$HOME/.config/dna-memory/profile.json"
```

如果你已经有 Obsidian vault，只需把 `knowledge_root` 指向该 vault，并把
`managed_memory_dir` 设为 DNA Memory 可管理的子目录。不要让工具接管整个 vault。

## 3. 初始化并检查

```bash
python3 dna.py memory reindex --json
python3 dna.py memory status --json
```

预期结果：`truth_root_exists` 为 `true`，数据库位于 profile 指定位置。

## 4. 配置客户端

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

```bash
codex mcp get dna-memory
claude mcp get dna-memory
hermes mcp test dna-memory
```

Claude Desktop 的配置方式不同，见
[统一 MCP 与客户端接入](docs/mcp-and-client-adapters.md)。

## 5. 做一次真实闭环验收

在任一已接入客户端中：

1. 调用 `memory_remember` 写入一条无敏感信息的测试结论。
2. 用该结论中的独特关键词调用 `memory_recall`。
3. 确认返回相同 memory ID。
4. 调用 `memory_feedback`，`outcome` 设为 `useful`。
5. 在另一个客户端再次召回同一关键词。

只看到 MCP 配置不代表系统已经生效。写入、同端召回、跨端召回和反馈都成功，
才算完成验收。验收后可以用新记忆的 `supersedes` 替换测试结论，或从受管
Markdown 目录删除它并执行 `memory reindex`。

## 6. 安装统一行为 Skill

把 `skills/dna-memory-loop` 复制到共享 Skill 真源，注册后 dry-run：

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/dna-memory-loop "$HOME/.agents/skills/"
cp assets/skills.example.json "$HOME/.config/dna-memory/skills.json"

python3 dna.py skills doctor --json
python3 dna.py skills sync --json
python3 dna.py skills sync --apply --json
```

## 7. 观察是否产生价值

```bash
python3 dna.py memory coverage --json
python3 dna.py memory value --json
```

分别看四件事：客户端是否被覆盖、长期记忆是否实际增长、召回是否命中、
命中后是否获得 `useful` 反馈。候选事件数量很大但长期结论和有用召回不增长，
不代表系统有价值。

## 8. 维护

```bash
python3 dna.py memory maintain daily --json
python3 dna.py memory maintain weekly --json
python3 dna.py memory maintain monthly --json
```

- daily：审查并结晶安全提案，清理过期候选。
- weekly：daily + SQLite 备份与压缩。
- monthly：weekly + 完整性检查与 Markdown 重建核对。

完整会话仍属于各客户端。DNA Memory 不应复制完整 transcript，也不应保存
token、API key、私钥或账号配置。
