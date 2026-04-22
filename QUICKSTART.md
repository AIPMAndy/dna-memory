# 🚀 DNA Memory 快速上手指南

> 30 秒学会使用 DNA Memory 的核心功能

## 核心功能（只需要这 3 个）

### 1. 记录记忆（remember）

```bash
python3 scripts/evolve.py remember "内容" --type [类型] --importance [0-1]
```

**类型**：
- `preference` - 用户偏好
- `error` - 错误教训
- `fact` - 事实知识
- `skill` - 技能方法
- `pattern` - 模式规律

**示例**：
```bash
# 记录用户偏好
python3 scripts/evolve.py remember "Andy 喜欢简洁直接的回复" -t preference -i 0.9

# 记录错误教训
python3 scripts/evolve.py remember "飞书 API 调用时必须传 content 参数" -t error -i 0.95

# 记录技能方法
python3 scripts/evolve.py remember "用马斯克五步法分析问题：质疑需求→删除→简化→加速→自动化" -t skill -i 0.85
```

### 2. 搜索记忆（recall）

```bash
# 基础搜索
python3 scripts/enhanced_recall.py "关键词" --limit 5

# 按类型搜索
python3 scripts/enhanced_recall.py --type error --limit 5

# 搜索最近记忆
python3 scripts/enhanced_recall.py --recent 7 --limit 5
```

**示例**：
```bash
# 搜索飞书相关记忆
python3 scripts/enhanced_recall.py "飞书" --limit 5

# 搜索所有错误记忆（避免重复踩坑）
python3 scripts/enhanced_recall.py --type error --limit 10

# 搜索最近 7 天的记忆
python3 scripts/enhanced_recall.py --recent 7 --limit 5
```

### 3. 后台维护（daemon）

```bash
# 启动 daemon（自动 reflect + decay）
python3 scripts/dna_memory_daemon.py start

# 查看状态
python3 scripts/dna_memory_daemon.py status

# 停止 daemon
python3 scripts/dna_memory_daemon.py stop
```

---

## 推荐工作流

### 任务开始前（必须）

```bash
# 1. 搜索相关记忆
python3 scripts/enhanced_recall.py "任务关键词" --limit 5

# 2. 搜索错误记忆（避免重复踩坑）
python3 scripts/enhanced_recall.py --type error --limit 5
```

### 任务结束后（必须）

```bash
# 1. 记录新学到的东西
python3 scripts/evolve.py remember "学到的内容" -t fact -i 0.8

# 2. 如果被纠正，记录错误
python3 scripts/evolve.py remember "纠正内容" -t error -i 0.9

# 3. 如果发现新偏好，记录偏好
python3 scripts/evolve.py remember "偏好内容" -t preference -i 0.85
```

---

## 快捷命令（可选）

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
# DNA Memory 快捷命令
alias dna-remember='python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py remember'
alias dna-recall='python3 ~/.openclaw/skills/dna-memory/scripts/enhanced_recall.py'
alias dna-stats='python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py stats'
alias dna-daemon='python3 ~/.openclaw/skills/dna-memory/scripts/dna_memory_daemon.py'
```

然后使用：
```bash
dna-remember "内容" -t preference -i 0.9
dna-recall "关键词"
dna-stats
```

---

## 常用命令速查

```bash
# 查看统计
python3 scripts/evolve.py stats

# 手动反思（归纳模式）
python3 scripts/evolve.py reflect

# 查看所有记忆
python3 scripts/evolve.py recall ""

# 删除重复记忆
python3 scripts/evolve.py dedupe
```

---

## 高级功能（可选）

如果你需要更多功能，可以查看：
- `memory_quality.py` - 记忆质量评估
- `memory_graph.py` - 记忆关联图谱
- `memory_extractor.py` - 自动记忆提取
- `session_memory.py` - 会话级记忆

详细文档见 [README.md](./README.md)

---

## 常见问题

### Q: 记忆太多了怎么办？
A: daemon 会自动 decay（衰减）低权重记忆，也可以手动执行 `python3 scripts/evolve.py dedupe` 删除重复记忆。

### Q: 如何确保 daemon 一直运行？
A: 可以配置 launchd（macOS）或 systemd（Linux）开机自启，详见 README.md。

### Q: 记忆存储在哪里？
A: `memory/memory.db`（SQLite 数据库）

### Q: 如何备份记忆？
A: 直接复制 `memory/memory.db` 文件即可。

---

**记住：DNA Memory 的核心是 3 个功能 - remember / recall / daemon。其他都是可选的。**
