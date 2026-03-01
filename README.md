# 🧬 DNA Memory

> 让 AI Agent 像人脑一样学习和成长

人脑不是硬盘。人脑会遗忘、会归纳、会反思。DNA Memory 让 Agent 做到同样的事。

## 💡 核心差异

| 传统记忆 | DNA Memory |
|----------|------------|
| 无差别存储 | 三层记忆架构 |
| 永不遗忘 | 主动遗忘机制 |
| 零散信息 | 自动归纳模式 |
| 被动记录 | 反思循环 |
| 孤立记忆 | 知识图谱关联 |

## 🚀 安装

```bash
# 克隆到 OpenClaw skills 目录
git clone https://github.com/AIPMAndy/dna-memory.git ~/.openclaw/skills/dna-memory

# 或手动复制
cp -r dna-memory ~/.openclaw/skills/
```

**依赖**: Python 3.8+ （无额外依赖）

## 📖 使用方法

### 基础命令

```bash
# 记录新记忆
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py remember "Andy 喜欢简洁回复" -t preference -i 0.9

# 回忆相关内容
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py recall "Andy"

# 反思归纳（从短期记忆提取模式）
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py reflect

# 遗忘衰减（清理低权重记忆）
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py decay

# 建立记忆关联
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py link mem_001 mem_002 -r "因果"

# 查看统计
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py stats
```

### 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `fact` | 事实信息 | "Andy 的微信是 AIPMAndy" |
| `preference` | 用户偏好 | "Andy 喜欢简洁直接的回复" |
| `skill` | 学到的技能 | "飞书 API 限流时要分段请求" |
| `error` | 犯过的错误 | "不要用 rm，用 trash" |
| `pattern` | 归纳的模式 | "推送 GitHub 前先检查网络" |
| `insight` | 深层洞察 | "Andy 更看重效率而非完美" |

## 🏗️ 三层记忆架构

```
┌─────────────────────────────────────┐
│  工作记忆 (Working Memory)          │
│  当前会话 → 会话后自动筛选           │
└──────────────┬──────────────────────┘
               ↓ 筛选
┌─────────────────────────────────────┐
│  短期记忆 (Short-term Memory)       │
│  7天内 → 带衰减权重，不用会遗忘      │
└──────────────┬──────────────────────┘
               ↓ 巩固
┌─────────────────────────────────────┐
│  长期记忆 (Long-term Memory)        │
│  持久保存 → 验证过的知识和模式       │
└─────────────────────────────────────┘
```

## 📁 数据存储

```
~/.openclaw/workspace/memory/
├── short_term.json   # 短期记忆
├── long_term.json    # 长期记忆
├── patterns.md       # 归纳的认知模式
└── graph.json        # 记忆关联图谱
```

## ⚙️ 配置

编辑 `assets/config.json`：

```json
{
  "decay_days": 7,        // 几天后开始衰减
  "decay_rate": 0.1,      // 每次衰减多少
  "forget_threshold": 0.2, // 低于此值被遗忘
  "reflect_trigger": 20,   // 积累多少条触发反思
  "max_short_term": 100,   // 短期记忆上限
  "max_long_term": 500     // 长期记忆上限
}
```

## 🔄 记忆强化规则

| 事件 | 权重变化 |
|------|----------|
| 被访问/使用 | +0.1 |
| 被用户确认正确 | +0.2 |
| 被用户纠正 | 标记为错误 |
| 7天未访问 | -0.1 |
| 关联到其他记忆 | +0.05 |
| 被归纳为模式 | 升级为长期记忆 |

## 🤝 与 OpenClaw 集成

DNA Memory 是一个 OpenClaw Skill。安装后，Agent 会在相关场景自动调用：

- 用户说"记住这个" → 触发 remember
- Agent 需要上下文 → 触发 recall
- 定期维护 → 触发 reflect 和 decay

详见 [SKILL.md](SKILL.md) 了解完整的 Agent 集成说明。

## 📄 License

Apache 2.0

## 👨‍💻 作者

**AI酋长Andy** | 前腾讯/百度 AI 产品专家

- 微信：AIPMAndy
- GitHub：[@AIPMAndy](https://github.com/AIPMAndy)

---

**让 Agent 真正学会成长** 🧬
