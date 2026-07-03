<div align="center">

# 🧬 DNA Memory

**让 AI Agent 像人脑一样学习、强化、遗忘与进化**

[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-3.2-green)](https://github.com/AIPMAndy/dna-memory/releases)

[English](./README_EN.md) | **简体中文** | [快速上手](./QUICKSTART.md)

</div>

---

> **大多数 AI 记忆系统只是在"存储"。**  
> **DNA Memory 解决的是: AI 如何像人一样学习、强化与进化。**

## 💡 为什么需要 DNA Memory？

你是否遇到过这些问题：

- ❌ **AI 总是忘记你的偏好**：每次都要重复"我喜欢简洁的回复"
- ❌ **犯过的错误反复出现**：上次说过不要用某个工具，这次又推荐
- ❌ **记忆混乱无序**：存了一堆碎片，检索时找不到关键信息
- ❌ **性能问题**：记忆越多越卡，最后弃用

**DNA Memory 三大核心价值：**

1. **🎯 真正有效的记忆** - 高优先级记忆自动同步到 Claude Code，每次对话都会被加载
2. **⚡️ 轻量高性能** - 500 条记忆 < 0.1MB，查询 < 0.5ms，不影响 AI 使用体验
3. **🧠 自动升华** - 不调用 LLM，纯算法实现记忆强化、衰减、晋升，零成本

---

## 🚀 5 分钟快速上手

```bash
# 1. 克隆到技能目录
git clone https://github.com/AIPMAndy/dna-memory.git ~/.cc-switch/skills/dna-memory
# 或 ~/.claude/skills/dna-memory

cd ~/.cc-switch/skills/dna-memory

# 2. 记录一条高优先级偏好
python3 scripts/store_memory.py \
  --content "浏览器操作永远优先使用 Kimi webbridge MCP 工具" \
  --type preference \
  --weight 0.95

# 3. 同步到 Claude Code Memory（每次对话都会加载）
python3 scripts/sync_to_claude.py

# 4. 查看统计
python3 dna.py manage stats

# 5. 搜索记忆
python3 dna.py manage search "浏览器"
```

**完成！** 你的 AI 现在会记住这条偏好。

---

## ✨ 核心能力

### 1. 📊 记忆管理界面

```bash
# 查看所有记忆
python3 dna.py manage list --limit 10

# 搜索记忆（FTS5 全文搜索）
python3 dna.py manage search "webbridge"

# 查看详情
python3 dna.py manage view 9

# 更新记忆
python3 dna.py manage update 9 --weight 1.0 --type preference

# 删除记忆
python3 dna.py manage delete 9 --confirm

# 统计信息
python3 dna.py manage stats
```

**输出示例：**
```
📊 DNA Memory 统计信息
============================================================
总记忆数: 10
高优先级记忆 (≥0.8): 1
数据库大小: 0.11 MB

按类型分布:
  preference  :   2 条 (平均权重: 0.74)
  pattern     :   4 条 (平均权重: 0.52)
  fact        :   2 条 (平均权重: 0.56)
  error       :   1 条 (平均权重: 0.52)
```

### 2. 🧠 轻量级记忆升华

**零成本、纯算法、可配置频率**

```bash
# 查看升华状态
python3 dna.py reflect status

# 执行升华
python3 dna.py reflect run

# 强制执行（忽略时间间隔）
python3 dna.py reflect run --force

# 查看配置
python3 dna.py reflect config
```

**升华机制：**
- ✅ **频繁访问 → 权重提升**：每次调用 +0.05
- ✅ **长期不用 → 权重衰减**：每天 -0.01
- ✅ **晋升长期记忆**：权重 ≥ 0.8 且访问 ≥ 3 次
- ✅ **发现相似记忆**：提示合并建议（不自动执行）

**完全不调用 LLM，零 API 成本！**

### 3. ⚡️ 性能监控

```bash
# 检查性能
python3 dna.py monitor check

# 自动清理（性能危险时）
python3 dna.py monitor auto-clean
```

**性能保证：**
```
🔍 DNA Memory 性能报告
==================================================
数据库大小: 0.11 MB / 5 MB
记忆数量: 10 / 500
查询速度: 0.34 ms
健康度: 98%
状态: HEALTHY

✅ 性能良好
```

**性能限制：**
- 最大记忆数：500 条（可配置，默认降低以保持轻量）
- 数据库上限：5 MB
- 查询时间：< 50ms
- 自动清理：权重 < 0.25 且超过 60 天未访问

### 4. 🔄 自动同步到 Claude Code Memory

高优先级记忆（weight ≥ 0.8）会自动同步到 Claude Code Memory，**每次对话都会被加载**！

```bash
# 手动同步
python3 dna.py sync

# 或通过 launchd 自动同步（每小时）
launchctl load ~/Library/LaunchAgents/com.andy.dna-memory-sync.plist
```

### 5. 🤖 智能问答（Memory-Enhanced Q&A）

AI 回答时自动注入相关记忆，让 AI 更懂你：

```bash
# 使用默认 Agent
python3 dna.py ask "浏览器操作应该用什么工具？"

# 指定 Agent
python3 dna.py ask "如何优化性能？" --agent hermes

# 调整检索数量
python3 dna.py ask "调试技巧" --recall-limit 10
```

---

## 🎯 三层记忆架构

```text
工作记忆 (Working Memory)
  ↓ 筛选
短期记忆 (Short-term Memory)
  ↓ 巩固 / 晋升
长期记忆 (Long-term Memory)
```

| 层级 | 作用 | 典型内容 | 权重范围 |
|------|------|----------|----------|
| 工作记忆 | 当前会话临时上下文 | 本轮任务、刚发生的事 | 0.3-0.5 |
| 短期记忆 | 近期重要信息 | 用户偏好、近期经验、错误教训 | 0.5-0.8 |
| 长期记忆 | 稳定知识与模式 | 规则、技能、长期偏好、归纳模式 | 0.8-1.0 |

---

## 📦 记忆类型

| 类型 | 说明 | 示例 | 推荐权重 |
|------|------|------|----------|
| `preference` | 用户偏好、习惯 | "回复要简洁直接" | 0.8-1.0 |
| `pattern` | 工作模式、流程 | "马斯克五步法" | 0.6-0.9 |
| `skill` | 技能、工具使用 | "如何使用 lark-cli" | 0.5-0.8 |
| `error` | 错误教训 | "不要用 selenium，用 webbridge" | 0.7-0.9 |
| `fact` | 事实性信息 | "用户是 AI 产品专家" | 0.5-0.7 |
| `insight` | 洞察、总结 | "内容质量不是问题，缺付费入口" | 0.6-0.9 |

---

## ⚙️ 配置文件

编辑 `assets/config.json`：

```json
{
  "_comment_performance": "性能配置",
  "max_total_memories": 500,           // 最大记忆数（降低保持轻量）
  "cleanup_threshold": 0.25,           // 清理阈值
  "archive_after_days": 90,            // 归档天数

  "_comment_sync": "同步配置",
  "sync_weight_threshold": 0.8,        // 同步权重阈值
  "sync_max_memories": 20,             // 最多同步数

  "_comment_reflection": "升华配置（零成本）",
  "reflection": {
    "enabled": true,                   // 启用升华
    "interval_hours": 24,              // 升华频率（小时）
    "min_memories_for_reflection": 5,  // 最少记忆数
    "weight_boost_per_recall": 0.05,   // 每次调用增加权重
    "weight_decay_per_day": 0.01       // 每天衰减权重
  }
}
```

---

## 🛠️ 安装位置灵活

DNA Memory 自动检测安装位置，支持：

- ✅ `~/.cc-switch/skills/dna-memory`
- ✅ `~/.claude/skills/dna-memory`
- ✅ `~/.openclaw/skills/dna-memory`

无需修改代码，自动适配！

---

## 🌟 项目特色

### 1. 真正轻量
- **核心只依赖 Python 标准库 + SQLite**
- **500 条记忆 < 0.1MB**
- **查询 < 0.5ms**
- **不影响 AI 使用性能**

### 2. 零 API 成本
- **记忆升华完全不调用 LLM**
- **纯算法实现强化、衰减、晋升**
- **长期运行零额外成本**

### 3. 真正有效
- **高优先级记忆自动同步到 Claude Code Memory**
- **每次对话都会被加载**
- **AI 真的会记住你的偏好**

### 4. 可管理
- **完整的命令行界面**
- **查看、搜索、编辑、删除**
- **统计、监控、升华**
- **完全掌控你的记忆**

---

## 📚 多 Agent 支持

DNA Memory 支持多个 AI Agent：

- ✅ **Claude CLI** (v2.1.181+)
- ✅ **Hermes** (v0.17.0+)
- ⚠️ **Codex** (需要重新安装)

自动检测可用 Agent，统一调用接口。

---

## 🔧 开发指南

```bash
# 克隆仓库
git clone https://github.com/AIPMAndy/dna-memory.git
cd dna-memory

# 运行测试
python3 scripts/memory_manager.py stats
python3 scripts/lightweight_monitor.py check
python3 scripts/lightweight_reflection.py status

# 查看帮助
python3 dna.py help
```

---

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

## 🤝 贡献

欢迎 PR、Issue、建议！

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 🙏 致谢

灵感来源：
- 人类记忆的工作原理
- Ebbinghaus 遗忘曲线
- 强化学习理论

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

[GitHub](https://github.com/AIPMAndy/dna-memory) | [文档](./docs) | [快速上手](./QUICKSTART.md)

Made with ❤️ by [Andy](https://github.com/AIPMAndy)

</div>
