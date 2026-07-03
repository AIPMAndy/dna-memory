---
name: dna-memory
description: "DNA Memory system with auto-sync to Claude Memory. Records preferences, skills, patterns, and errors with automatic context loading. Use when user says 记住/remember/学到了/别忘了."
user-invocable: true
triggers:
  - remember this
  - 记住这个
  - 记录偏好
  - 学到了
  - 别忘了
  - dna memory
---

# DNA Memory - 真正会记住的记忆系统

## 核心改进：解决"老记不住"的问题

**之前的问题**：
- DNA Memory 有完整的记忆系统，但记忆存在独立数据库中
- AI 看不到这些记忆，所以无法应用
- 用户说"记住用 webbridge"，AI 下次还是忘记

**现在的解决方案**：
- **双轨制**：DNA Memory 负责存储和管理，Claude Memory 负责自动加载
- **自动同步**：高优先级记忆（weight >= 0.8 或 type=preference）自动同步到 Claude Memory
- **真正生效**：每次对话开始时，这些记忆会自动出现在系统提示词中

---

## 使用方法

### 1. 记录新记忆

```bash
# 记录偏好（自动高优先级）
python3 ~/.cc-switch/skills/dna-memory/scripts/evolve.py remember \
  "浏览器操作用 webbridge" \
  -t preference \
  -i 0.95

# 记录技能
python3 ~/.cc-switch/skills/dna-memory/scripts/evolve.py remember \
  "飞书 API 限流时分段请求" \
  -t skill \
  -i 0.8

# 记录错误教训
python3 ~/.cc-switch/skills/dna-memory/scripts/evolve.py remember \
  "不要用 rm 删除文件，用 trash" \
  -t error \
  -i 0.9
```

### 2. 同步到 Claude Memory（让记忆生效）

```bash
# 手动同步
python3 ~/.cc-switch/skills/dna-memory/scripts/sync_to_claude.py

# 预览要同步的记忆
python3 ~/.cc-switch/skills/dna-memory/scripts/sync_to_claude.py --dry-run
```

### 3. 搜索记忆

```bash
# 基础搜索
python3 ~/.cc-switch/skills/dna-memory/scripts/evolve.py recall "webbridge"

# 按类型搜索
python3 ~/.cc-switch/skills/dna-memory/scripts/evolve.py recall "type:preference"

# 增强搜索（智能排序）
python3 ~/.cc-switch/skills/dna-memory/scripts/enhanced_recall.py "飞书 API" --limit 5
```

### 4. 查看统计

```bash
python3 ~/.cc-switch/skills/dna-memory/scripts/evolve.py stats
```

---

## 工作流程

```text
用户: "记住这个，浏览器操作用 webbridge"
  ↓
1. 记录到 DNA Memory 数据库
   python3 scripts/evolve.py remember "..." -t preference -i 0.95
  ↓
2. 同步到 Claude Memory
   python3 scripts/sync_to_claude.py
  ↓
3. 下次对话自动加载
   Claude Code 读取 MEMORY.md → 加载 synced-preferences.md
  ↓
4. AI 自动应用
   看到 webbridge 偏好 → 优先使用 webbridge
```

---

## 记忆分类与优先级

| 类型 | 说明 | 重要性阈值 | 同步到 Claude |
|------|------|-----------|--------------|
| `preference` | 用户偏好 | 自动高优先级 | ✅ 总是同步 |
| `skill` | 学到的技能 | >= 0.8 | ✅ 高权重时同步 |
| `pattern` | 归纳的模式 | >= 0.8 | ✅ 高权重时同步 |
| `error` | 犯过的错误 | >= 0.8 | ✅ 高权重时同步 |
| `fact` | 事实信息 | >= 0.8 | ⚠️ 可选 |
| `insight` | 深层洞察 | >= 0.8 | ✅ 高权重时同步 |

**同步规则**：
- Weight >= 0.8 的记忆会自动同步
- Type = preference 的记忆无论权重都会同步
- 同步后的记忆出现在 `~/.claude/projects/*/memory/synced-*.md`
- MEMORY.md 自动更新索引

---

## DNA Memory 的核心功能

### 三层记忆架构
```text
工作记忆 (Working) → 当前会话临时信息
  ↓ 筛选
短期记忆 (Short-term) → 近期重要信息，带权重衰减
  ↓ 巩固
长期记忆 (Long-term) → 稳定知识与模式
```

### 智能强化与遗忘
- 高频使用 → 权重提升
- 长期不访问 → 权重衰减
- 低权重记忆 → 自动清理
- 高价值记忆 → 晋升到长期

### 反思机制
```bash
# 手动反思（提炼模式）
python3 scripts/evolve.py reflect

# 后台自动反思（daemon）
python3 scripts/dna_memory_daemon.py start
```

---

## 自动化设置

### 1. 启动后台守护进程

```bash
# 启动（自动 reflect + decay）
python3 ~/.cc-switch/skills/dna-memory/scripts/dna_memory_daemon.py start

# 查看状态
python3 ~/.cc-switch/skills/dna-memory/scripts/dna_memory_daemon.py status

# 停止
python3 ~/.cc-switch/skills/dna-memory/scripts/dna_memory_daemon.py stop
```

### 2. 配置自动同步（推荐）

创建 cron 任务，每小时同步一次：

```bash
# 编辑 crontab
crontab -e

# 添加（每小时同步）
0 * * * * /usr/bin/python3 ~/.cc-switch/skills/dna-memory/scripts/sync_to_claude.py
```

或使用 launchd（macOS 推荐）：

```bash
# 创建 plist 文件
cat > ~/Library/LaunchAgents/com.andy.dna-memory-sync.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.andy.dna-memory-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/andy/.cc-switch/skills/dna-memory/scripts/sync_to_claude.py</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

# 加载
launchctl load ~/Library/LaunchAgents/com.andy.dna-memory-sync.plist
```

---

## 验证记忆是否生效

### 方法 1：查看同步文件

```bash
# 查看同步的偏好
cat ~/.claude/projects/-Users-andy-Documents-AICode/memory/synced-preferences.md

# 查看索引
cat ~/.claude/projects/-Users-andy-Documents-AICode/memory/MEMORY.md
```

### 方法 2：测试 AI 行为

在新对话中测试：
```
用户: 帮我打开 GitHub 看一下
AI: （应该自动使用 mcp__webbridge__navigate 而不是问你怎么打开）
```

如果 AI 还是忘记了：
1. 检查记忆是否同步：`python3 scripts/sync_to_claude.py --dry-run`
2. 检查权重是否够高：`sqlite3 memory/memory.db "SELECT * FROM memory WHERE type='preference';"`
3. 手动提升权重：`python3 scripts/evolve.py promote --id <memory_id>`

---

## 故障排查

### "记忆没有生效"

**诊断步骤**：

1. 检查记忆是否存在
```bash
python3 scripts/evolve.py recall "webbridge"
```

2. 检查权重是否足够
```bash
sqlite3 memory/memory.db "SELECT id, weight, content FROM memory WHERE type='preference';"
```

3. 检查是否已同步
```bash
cat ~/.claude/projects/-Users-andy-Documents-AICode/memory/synced-preferences.md
```

4. 手动同步
```bash
python3 scripts/sync_to_claude.py
```

### "权重太低没有同步"

```bash
# 提升权重
python3 scripts/evolve.py promote --id <memory_id>

# 或直接修改
sqlite3 memory/memory.db "UPDATE memory SET weight=0.95 WHERE id=<memory_id>;"

# 重新同步
python3 scripts/sync_to_claude.py
```

---

## 与 CLAUDE.md 的关系

- **CLAUDE.md**: 项目级的工作规范（提交到 git）
- **DNA Memory**: 个人偏好和动态学习（不提交 git）
- **synced-*.md**: 自动同步的高优先级记忆（每次对话加载）

**优先级**：synced-*.md > MEMORY.md > CLAUDE.md

当有冲突时，个人记忆优先（因为是用户明确反馈的）。

---

## 最佳实践

### ✅ 应该记录的

- **反复被忘记的偏好**（如"用 webbridge"）
- **从错误中学到的教训**（如"GitHub push 要重试"）
- **项目特定的约束**（如"这个项目用 Supabase"）
- **工具使用的优先级**（如"飞书文档用 /lark-doc"）

### ❌ 不应该记录的

- 代码本身可以表达的内容
- git 历史中已有的信息
- 临时的、会话级的信息
- 一次性的指令

### 💡 记录时的技巧

1. **具体明确**："用 webbridge" 而不是 "用更好的工具"
2. **包含 Why**："用 webbridge，因为 Andy 反复强调但经常被忘记"
3. **高权重**：重要偏好用 0.9-0.95
4. **立即同步**：记录后马上运行 `sync_to_claude.py`

---

## 技术架构

```text
┌─────────────────────────────────────────────┐
│  DNA Memory (存储层)                         │
│  - SQLite 数据库                             │
│  - 三层记忆架构                              │
│  - 权重管理、衰减、反思                      │
│  - FTS5 全文搜索                             │
└─────────────────────────────────────────────┘
                    ↓
            sync_to_claude.py
        (同步 weight>=0.8 的记忆)
                    ↓
┌─────────────────────────────────────────────┐
│  Claude Memory (加载层)                      │
│  - synced-preferences.md                     │
│  - synced-patterns.md                        │
│  - MEMORY.md (索引)                          │
└─────────────────────────────────────────────┘
                    ↓
            每次对话自动加载
                    ↓
┌─────────────────────────────────────────────┐
│  AI 系统提示词                               │
│  - CLAUDE.md                                 │
│  - MEMORY.md + synced-*.md                   │
│  → AI 看到并应用记忆                         │
└─────────────────────────────────────────────┘
```

---

## 总结：为什么这个方案能解决"老记不住"

1. **分离关注点**
   - DNA Memory：专注记忆管理（存储、搜索、强化、遗忘）
   - Claude Memory：专注上下文加载（每次对话自动生效）

2. **自动同步**
   - 不需要手动干预
   - 高优先级记忆自动出现在提示词中

3. **权重驱动**
   - 重要的记忆（weight >= 0.8）自动同步
   - 不重要的记忆不会污染上下文

4. **可验证**
   - 可以直接查看 synced-*.md 文件
   - 可以测试 AI 行为是否改变

5. **持续改进**
   - 记忆会根据使用频率强化
   - 不用的记忆会自动衰减
   - 反思机制提炼高层模式

---

**下一步**：设置自动同步（cron 或 launchd），然后就可以真正"丝滑使用"了。
