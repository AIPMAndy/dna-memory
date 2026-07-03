# 🚀 DNA Memory 快速上手指南

**5 分钟让你的 AI 拥有真正的记忆！**

---

## 步骤 1: 安装（30 秒）

```bash
# 克隆到 Claude Code 技能目录
git clone https://github.com/AIPMAndy/dna-memory.git ~/.cc-switch/skills/dna-memory

# 进入目录
cd ~/.cc-switch/skills/dna-memory
```

**支持的安装位置：**
- `~/.cc-switch/skills/dna-memory` ✅
- `~/.claude/skills/dna-memory` ✅
- `~/.openclaw/skills/dna-memory` ✅

---

## 步骤 2: 记录第一条记忆（1 分钟）

```bash
# 记录一条高优先级偏好
python3 scripts/store_memory.py \
  --content "我喜欢简洁直接的回复，不要废话" \
  --type preference \
  --weight 0.9

# 再记录一条技能
python3 scripts/store_memory.py \
  --content "使用 lark-cli 操作飞书文档" \
  --type skill \
  --weight 0.7
```

**记忆类型：**
- `preference` - 用户偏好
- `error` - 错误教训
- `fact` - 事实知识
- `skill` - 技能方法
- `pattern` - 工作模式
- `insight` - 洞察总结

---

## 步骤 3: 同步到 Claude Code（30 秒）

```bash
# 同步高优先级记忆到 Claude Code Memory
python3 scripts/sync_to_claude.py
```

**效果：** 权重 ≥ 0.8 的记忆会自动同步到 Claude Code Memory，**每次对话都会被加载**！

---

## 步骤 4: 查看和管理记忆（1 分钟）

```bash
# 查看统计
python3 dna.py manage stats

# 列出所有记忆
python3 dna.py manage list --limit 10

# 搜索记忆
python3 dna.py manage search "简洁"

# 查看详情
python3 dna.py manage view 1

# 更新记忆权重
python3 dna.py manage update 1 --weight 0.95
```

---

## 步骤 5: 启用自动升华（1 分钟）

```bash
# 查看升华状态
python3 dna.py reflect status

# 执行一次升华
python3 dna.py reflect run

# 配置自动升华（可选）
# 编辑 assets/config.json 中的 reflection 配置
```

**升华机制（零 API 成本）：**
- 频繁访问的记忆 → 权重提升
- 长期不用的记忆 → 权重衰减
- 高权重记忆 → 晋升长期记忆

---

## 步骤 6: 监控性能（30 秒）

```bash
# 检查性能
python3 dna.py monitor check

# 如果需要清理
python3 dna.py monitor auto-clean
```

---

## 🎯 常见使用场景

### 场景 1: 记录用户偏好

```bash
python3 scripts/store_memory.py \
  --content "用户是 AI 产品专家，喜欢技术细节和原理" \
  --type preference \
  --weight 0.9
```

### 场景 2: 记录错误教训

```bash
python3 scripts/store_memory.py \
  --content "不要使用 selenium 控制浏览器，应该用 Kimi webbridge MCP 工具" \
  --type error \
  --weight 0.85
```

### 场景 3: 记录工作模式

```bash
python3 scripts/store_memory.py \
  --content "复杂任务先用 /brainstorming 分析，再用 /writing-plans 规划" \
  --type pattern \
  --weight 0.75
```

### 场景 4: 记录技能知识

```bash
python3 scripts/store_memory.py \
  --content "使用 lark-doc 读取飞书文档，优先 outline/section 模式" \
  --type skill \
  --weight 0.7
```

---

## 💡 权重设置建议

| 权重范围 | 类型 | 说明 | 是否同步到 Claude Code |
|----------|------|------|------------------------|
| 0.9-1.0 | 核心偏好 | 用户最重要的偏好，绝对不能忘 | ✅ 是 |
| 0.8-0.9 | 重要规则 | 重要的工作规则、错误教训 | ✅ 是 |
| 0.6-0.8 | 常用技能 | 经常用到的技能、模式 | ❌ 否 |
| 0.4-0.6 | 一般信息 | 一般性知识、事实 | ❌ 否 |
| < 0.4 | 临时记忆 | 临时性的、可能过时的信息 | ❌ 否 |

---

## 🔄 自动化配置（可选）

### 配置自动同步（每小时）

```bash
# 加载 launchd 配置
launchctl load ~/Library/LaunchAgents/com.andy.dna-memory-sync.plist

# 查看状态
launchctl list | grep dna-memory

# 卸载
launchctl unload ~/Library/LaunchAgents/com.andy.dna-memory-sync.plist
```

---

## 📊 查看完整命令列表

```bash
python3 dna.py help
```

**输出：**
```
DNA Memory - 智能记忆管理系统

可用命令:
  manage    - 记忆管理（查看、搜索、编辑、删除）
  reflect   - 记忆升华（轻量级，不调用LLM）
  monitor   - 性能监控
  ask       - 智能问答（自动注入相关记忆）
  sync      - 同步高优先级记忆到 Claude Code Memory
```

---

## ❓ 常见问题

### Q1: 如何知道哪些记忆被同步了？

```bash
# 查看同步到 Claude Code 的记忆文件
cat ~/.claude/projects/*/memory/synced-preferences.md
```

### Q2: 记忆太多影响性能怎么办？

```bash
# 检查性能
python3 dna.py monitor check

# 自动清理低权重记忆
python3 dna.py monitor auto-clean
```

### Q3: 如何调整升华频率？

编辑 `assets/config.json`：

```json
{
  "reflection": {
    "interval_hours": 12  // 改为 12 小时一次
  }
}
```

### Q4: 如何删除错误的记忆？

```bash
# 搜索找到 ID
python3 dna.py manage search "错误关键词"

# 删除
python3 dna.py manage delete <ID> --confirm
```

---

## 🎉 完成！

现在你的 AI 有了真正的记忆系统！

**下一步：**
- 📚 阅读 [完整文档](./README.md)
- 🔧 查看 [性能优化指南](./PERFORMANCE_OPTIMIZATION.md)
- 🤝 参与 [贡献](./CONTRIBUTING.md)

---

**遇到问题？** [提交 Issue](https://github.com/AIPMAndy/dna-memory/issues)
