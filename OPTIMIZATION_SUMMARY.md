# DNA Memory 优化完成 - 真正丝滑使用指南

## ✅ 已解决的核心问题

**之前**：你说"记住用 webbridge"，AI 下次还是忘记
**现在**：记忆自动同步到 Claude Memory，每次对话自动加载并应用

## 🎯 验证：记忆已生效

### 1. 查看同步的记忆
```bash
cat ~/.claude/projects/-Users-andy-Documents-AICode/memory/synced-preferences.md
```

**当前已同步**：
- ✅ webbridge 优先使用（权重 0.95）

### 2. 查看 DNA Memory 中的所有记忆
```bash
cd ~/.cc-switch/skills/dna-memory
./dna stats
```

**当前共有 9 条记忆**：
- 1 条 fact (Andy 身份)
- 2 条 preference (webbridge + 不中断任务)
- 4 条 pattern (脚本优先/每日资讯/飞书文档/马斯克五步法)
- 1 条 insight (变现策略)
- 1 条 error (深度诊断教训)

---

## 🚀 使用方法（超简单）

### 记录新偏好（自动同步）
```bash
cd ~/.cc-switch/skills/dna-memory

# 方法1：用新的 wrapper（推荐）
./dna remember "你的偏好内容" -t preference -i 0.95

# 方法2：传统方式 + 手动同步
python3 scripts/evolve.py remember "内容" -t preference -i 0.95
python3 scripts/sync_to_claude.py
```

### 搜索记忆
```bash
./dna recall "关键词"
```

### 查看统计
```bash
./dna stats
```

### 手动同步
```bash
./dna sync
```

---

## ⚙️ 自动化设置（推荐）

### 方法1：Launchd（macOS 推荐）

创建自动同步任务，每小时同步一次：

```bash
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
    <key>StandardOutPath</key>
    <string>/tmp/dna-memory-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/dna-memory-sync-error.log</string>
</dict>
</plist>
EOF

# 加载
launchctl load ~/Library/LaunchAgents/com.andy.dna-memory-sync.plist

# 验证
launchctl list | grep dna-memory
```

### 方法2：简单的 cron（备选）

```bash
# 编辑 crontab
crontab -e

# 添加（每小时同步一次）
0 * * * * /usr/bin/python3 ~/.cc-switch/skills/dna-memory/scripts/sync_to_claude.py >> /tmp/dna-sync.log 2>&1
```

---

## 🧪 测试：验证记忆是否真的生效

### 测试 1：在新对话中测试 webbridge 偏好

**预期行为**：
- 当你说"帮我打开 GitHub 看一下"
- AI 应该自动使用 `mcp__webbridge__navigate`
- 而不是问你怎么打开或建议其他方法

### 测试 2：查看 AI 的上下文

在新对话中问：
```
你现在的记忆系统中有关于浏览器操作的偏好吗？
```

AI 应该能够回答：
```
有的，浏览器操作要优先使用 Kimi webbridge MCP 工具...
```

---

## 🔧 故障排查

### 问题1："AI 还是忘了"

**诊断**：
```bash
# 1. 检查记忆是否存在
cd ~/.cc-switch/skills/dna-memory
./dna recall "webbridge"

# 2. 检查是否已同步
cat ~/.claude/projects/-Users-andy-Documents-AICode/memory/synced-preferences.md

# 3. 检查权重
sqlite3 memory/memory.db "SELECT id, weight, type, content FROM memory WHERE content LIKE '%webbridge%';"
```

**解决**：
```bash
# 提升权重
python3 scripts/evolve.py promote --id <memory_id>

# 重新同步
./dna sync
```

### 问题2："权重不够高"

```bash
# 直接修改数据库
sqlite3 memory/memory.db "UPDATE memory SET weight=0.95 WHERE id=9;"

# 重新同步
./dna sync
```

### 问题3："MEMORY.md 没有索引"

```bash
# 查看索引
cat ~/.claude/projects/-Users-andy-Documents-AICode/memory/MEMORY.md

# 如果缺失，重新同步会自动添加
./dna sync
```

---

## 📊 当前记忆概览

### 高优先级记忆（已同步到 Claude）

1. **webbridge 优先** (preference, 0.95)
   - 浏览器操作永远优先使用 webbridge MCP 工具

### 其他重要记忆（weight < 0.8，暂未同步）

2. **不中断任务** (preference, 0.52)
   - 任务做到一半不要停下来问是否继续

3. **脚本优先模型兜底** (pattern, 0.52)
   - 确定性任务优先脚本/工具，不要先烧模型 token

4. **马斯克五步法** (pattern, 0.52)
   - 质疑需求 → 删除 → 简化 → 加速 → 自动化

5. **变现策略** (insight, 0.52)
   - 不是内容质量问题，而是缺少付费入口

6. **每日AI资讯格式** (pattern, 0.52)
   - 3:3:4 比例，3000-5000字

7. **飞书文档更新** (pattern, 0.52)
   - 必须 overwrite 模式重写

8. **深度诊断教训** (error, 0.52)
   - 工具在但不用 = 没有工具

**建议**：将重要的记忆提升权重到 0.8+，让它们也同步到 Claude Memory

```bash
# 提升重要记忆的权重
cd ~/.cc-switch/skills/dna-memory
python3 scripts/evolve.py promote --id 4  # 不中断任务
python3 scripts/evolve.py promote --id 1  # 马斯克五步法
python3 scripts/evolve.py promote --id 3  # 深度诊断教训

# 重新同步
./dna sync
```

---

## 🎓 最佳实践

### 1. 记录什么样的记忆？

**✅ 应该记录**：
- 反复被忘记的偏好（如 webbridge）
- 从错误中学到的教训
- 项目特定的约束
- 工具使用的优先级

**❌ 不应该记录**：
- 代码本身能表达的内容
- git 历史中的信息
- 临时的、一次性的信息

### 2. 如何设置权重？

- **0.95+**：关键偏好，每次必须遵守
- **0.8-0.9**：重要技能和模式
- **0.5-0.7**：一般记忆
- **< 0.5**：会被自动遗忘

### 3. 记录后立即同步

```bash
./dna remember "内容" -t preference -i 0.95
# wrapper 会自动同步

# 或
python3 scripts/evolve.py remember "内容" -t preference -i 0.95
./dna sync  # 手动同步
```

---

## 🔄 工作流建议

### 日常使用
```bash
# 1. 发现新偏好时记录
./dna remember "新发现的偏好" -t preference -i 0.9

# 2. 定期查看统计
./dna stats

# 3. 定期反思归纳
./dna reflect
```

### 如果设置了自动同步
- 记录后不需要手动同步
- 每小时自动同步一次
- 下次对话自动生效

### 如果没有自动同步
- 每次记录后手动 `./dna sync`
- 或每天运行一次同步

---

## 📝 下一步建议

1. **立即做**：设置自动同步（launchd 或 cron）
2. **本周做**：提升重要记忆的权重，让更多记忆生效
3. **长期做**：养成习惯，发现重要偏好时立即记录

---

## 🎉 总结

**DNA Memory 现在真正"丝滑"了**：

1. ✅ 记忆存储完整（SQLite + 三层架构 + 强化衰减）
2. ✅ 记忆自动同步（高优先级 → Claude Memory）
3. ✅ 记忆自动生效（每次对话自动加载）
4. ✅ 简单易用（./dna 命令 + 自动同步）
5. ✅ 可验证（可以查看文件，可以测试行为）

**核心突破**：解决了"记忆系统与 AI 上下文脱节"的根本问题。

**验证方法**：在新对话中测试"帮我打开 GitHub"，看 AI 是否自动用 webbridge。

---

**Created**: 2026-07-03
**Status**: ✅ 已优化完成，可丝滑使用
