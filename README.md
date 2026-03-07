<div align="center">

# 🧬 DNA Memory

**让 AI Agent 像人脑一样学习和成长**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-purple.svg)](https://openclaw.ai)
[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory)

[English](README_EN.md) | 简体中文

<img src="assets/demo.gif" alt="DNA Memory Demo" width="600">

</div>

---

人脑不是硬盘。人脑会遗忘、会归纳、会反思。

现有的 AI 记忆方案只解决了"存"的问题——DNA Memory 解决的是"学"的问题。

## 🆚 为什么需要 DNA Memory？

| 能力 | Mem0 | Zep | LangChain Memory | **DNA Memory** |
|------|:----:|:---:|:----------------:|:--------------:|
| 基础存储 | ✅ | ✅ | ✅ | ✅ |
| 向量检索 | ✅ | ✅ | ✅ | ✅ |
| 多层记忆架构 | ❌ | ⚠️ | ❌ | ✅ **3层** |
| 主动遗忘 | ❌ | ❌ | ❌ | ✅ |
| 自动归纳模式 | ❌ | ❌ | ❌ | ✅ |
| 反思循环 | ❌ | ❌ | ❌ | ✅ |
| 知识图谱关联 | ❌ | ⚠️ | ❌ | ✅ |
| 动态权重强化 | ❌ | ❌ | ❌ | ✅ |
| 零依赖本地运行 | ❌ | ❌ | ❌ | ✅ |

<details>
<summary>📊 竞品详细对比</summary>

### Mem0
- 云端记忆服务，需要 API 调用
- 数据存储在第三方服务器
- 按调用量收费

### Zep  
- 需要部署独立服务端
- 企业级方案，配置复杂
- 有基础的记忆分层但无归纳能力

### LangChain Memory
- 只是简单的上下文拼接
- 无持久化，重启丢失
- 没有真正的"学习"机制

### DNA Memory
- 🧠 **模拟人脑**：不只是存储，而是真正的学习
- 📉 **会遗忘**：不重要的信息自然衰减消失
- 📈 **会强化**：反复使用的记忆权重增加  
- 🔄 **会归纳**：从零散信息中提取认知模式
- 🕸️ **会关联**：建立记忆之间的知识图谱
- 🏠 **纯本地**：零依赖，数据完全在你手里

</details>

## 🚀 30秒快速开始

```bash
# 1. 克隆项目
git clone https://github.com/AIPMAndy/dna-memory.git ~/.openclaw/skills/dna-memory

# 2. 记录第一条记忆
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py remember "我喜欢简洁的回复" -t preference -i 0.9

# 3. 查看效果
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py stats
```

**零依赖**：只需要 Python 3.8+，不需要安装任何包。

## 🆕 最近更新（2026-03-08）

- ✅ 新增 `compact` 命令：一键压缩长期记忆，清理重复 Pattern。
- ✅ `reflect` 去重增强：基于 `signature` 避免重复归纳同一批来源记忆。
- ✅ 兼容历史数据：自动补全旧 Pattern 的 `signature/origin_type`，降低迁移成本。
- ✅ daemon 节流优化：仅在有新的 `remember` 写入后触发 `reflect`。
- ✅ daemon 间隔可配置：默认从 `assets/config.json` 读取反思/遗忘周期。

升级后建议执行一次：

```bash
python3 scripts/evolve.py compact
```

## 📖 核心命令

```bash
# 记录记忆
evolve.py remember "内容" -t 类型 -i 重要性(0-1)

# 回忆检索
evolve.py recall "关键词"

# 反思归纳（提取认知模式）
evolve.py reflect

# 遗忘衰减（清理低权重记忆）
evolve.py decay

# 压缩长期记忆（去重 + 补全旧 Pattern 签名）
evolve.py compact

# 建立关联
evolve.py link mem_001 mem_002 -r "因果关系"

# 列出/删除/导出
evolve.py list [-L 长期记忆]
evolve.py delete mem_xxx
evolve.py export -o backup.json
```

## 🏗️ 三层记忆架构

```
┌─────────────────────────────────────────────┐
│  🔴 工作记忆 (Working Memory)                │
│     当前会话的临时信息                        │
│     → 会话结束后自动筛选重要内容              │
└─────────────────┬───────────────────────────┘
                  ↓ 筛选
┌─────────────────────────────────────────────┐
│  🟡 短期记忆 (Short-term Memory)             │
│     近 7 天的重要信息                         │
│     → 带衰减权重，长期不用会逐渐遗忘          │
└─────────────────┬───────────────────────────┘
                  ↓ 巩固
┌─────────────────────────────────────────────┐
│  🟢 长期记忆 (Long-term Memory)              │
│     经过验证的持久知识                        │
│     → 归纳后的认知模式，高权重记忆            │
└─────────────────────────────────────────────┘
```

## 🔄 记忆进化机制

### 动态权重系统

| 事件 | 权重变化 | 说明 |
|------|:--------:|------|
| 被访问/使用 | **+0.1** | 用得多的记忆更重要 |
| 被用户确认 | **+0.2** | 正确的信息权重提升 |
| 被用户纠正 | 标记错误 | 创建新的正确记忆 |
| 7天未访问 | **-0.1** | 不用的逐渐遗忘 |
| 建立关联 | **+0.05** | 有连接的更稳固 |
| 归纳为模式 | **升级** | 进入长期记忆 |

### 自动归纳示例

```
📝 短期记忆中积累了多条相似记忆：

  "GitHub push 超时了"
  "GitHub clone 超时了"  
  "GitHub fetch 超时了"

💡 自动归纳为认知模式：

  "访问 GitHub 网络不稳定，需要重试机制"
  
  → 模式自动升级到长期记忆
```

## 📁 数据结构

```
~/.openclaw/workspace/memory/
├── short_term.json   # 短期记忆 (JSON)
├── long_term.json    # 长期记忆 (JSON)
├── patterns.md       # 认知模式 (Markdown)
├── graph.json        # 关联图谱 (JSON)
└── meta.json         # 统计数据
```

<details>
<summary>📄 记忆数据格式示例</summary>

```json
{
  "id": "mem_a1b2c3d4",
  "type": "preference",
  "content": "用户喜欢简洁直接的回复风格",
  "source": "user",
  "importance": 0.85,
  "created_at": "2026-03-01T10:30:00",
  "last_accessed": "2026-03-01T15:45:00",
  "access_count": 5,
  "tags": ["沟通", "风格"],
  "links": ["mem_x1y2z3"]
}
```

</details>

## ⚙️ 配置选项

编辑 `assets/config.json`：

```json
{
  "decay_days": 7,         // 多少天后开始衰减
  "decay_rate": 0.1,       // 每次衰减的权重
  "forget_threshold": 0.2, // 低于此权重被遗忘
  "reflect_trigger": 20,   // 积累多少条触发自动反思
  "max_short_term": 100,   // 短期记忆上限
  "max_long_term": 500,    // 长期记忆上限
  "auto_reflect": true,    // 是否允许自动反思
  "auto_reflect_interval_minutes": 30, // 自动反思最短间隔（分钟）
  "auto_decay": true,      // 是否允许自动遗忘
  "auto_decay_interval_hours": 24 // 自动遗忘最短间隔（小时）
}
```

## 💡 适用场景

| 场景 | 效果 |
|------|------|
| **个人 AI 助理** | 记住偏好习惯，越用越懂你 |
| **知识工作者** | 积累领域经验，形成专业模式 |
| **客服/销售 Agent** | 学习客户特征，优化沟通策略 |
| **自主 Agent** | 从错误中学习，持续自我优化 |
| **Agent 开发者** | 为你的 Agent 添加记忆进化能力 |

## 🤝 与 OpenClaw 集成

DNA Memory 是一个 [OpenClaw](https://openclaw.ai) Skill。安装后自动集成：

- 用户说"记住这个" → 触发 `remember`
- Agent 需要上下文 → 触发 `recall`  
- 定期维护 → 自动 `reflect` 和 `decay`

详见 [SKILL.md](SKILL.md) 了解完整集成说明。

## 🗺️ Roadmap

- [x] 三层记忆架构
- [x] 主动遗忘机制
- [x] 自动归纳模式
- [x] 知识图谱关联
- [ ] 向量语义检索（可选）
- [ ] 可视化记忆图谱
- [ ] 多 Agent 记忆共享
- [ ] Web UI 管理界面

## 🤲 贡献

欢迎 PR 和 Issue！

- 🐛 发现 Bug → [提交 Issue](https://github.com/AIPMAndy/dna-memory/issues)
- 💡 新功能建议 → [发起讨论](https://github.com/AIPMAndy/dna-memory/discussions)
- 🔧 代码贡献 → Fork & PR

## 📄 License

[Apache 2.0](LICENSE) - 可商用，可修改，保留署名即可。

---

<div align="center">

## 👨‍💻 作者

**AI酋长Andy**

前腾讯/百度 AI 产品专家 → 大模型独角兽 VP → 创业 CEO

现专注于 AI 商业化落地，帮助创始人用 AI 放大商业和影响力

[![微信](https://img.shields.io/badge/微信-AIPMAndy-07C160?logo=wechat&logoColor=white)](# "扫码添加")
[![GitHub](https://img.shields.io/badge/GitHub-AIPMAndy-181717?logo=github)](https://github.com/AIPMAndy)
[![Twitter](https://img.shields.io/badge/Twitter-@pmai_andy-1DA1F2?logo=twitter&logoColor=white)](https://twitter.com/pmai_andy)

---

**如果这个项目对你有帮助，请给一个 ⭐ Star！**

这是对作者最大的支持 🙏

</div>
