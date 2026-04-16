<div align="center">

# 🧬 DNA Memory

**让 AI Agent 像人脑一样学习、强化、遗忘与归纳**

[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![OpenClaw](https://img.shields.io/badge/Built%20for-OpenClaw-purple)](https://github.com/openclaw/openclaw)

[English](./README_EN.md) | **简体中文**

</div>

---

> 大多数 AI 记忆系统只是在“存”。
> **DNA Memory** 想解决的是：**AI 如何像人一样学习与进化。**

它不是简单的 memory store，而是一套带有：
- **三层记忆架构**
- **权重强化 / 衰减遗忘**
- **反思归纳（reflect）**
- **长期记忆晋升（promote）**
- **重复记忆清理（dedupe）**
- **FTS5 全文 recall 搜索**
- **后台 daemon 自动维护**

的 Agent 记忆系统。

---

## 🆚 为什么不是普通 Memory？

| 能力 | Mem0 | Zep | LangChain Memory | **DNA Memory** |
|------|:----:|:---:|:----------------:|:--------------:|
| 基础存储 | ✅ | ✅ | ✅ | ✅ |
| 向量/语义检索 | ✅ | ✅ | ✅ | ⚠️ 可扩展 |
| 多层记忆架构 | ❌ | ⚠️ | ❌ | ✅ **工作/短期/长期** |
| 主动遗忘 | ❌ | ❌ | ❌ | ✅ |
| 自动反思 | ❌ | ❌ | ❌ | ✅ |
| 模式归纳 | ❌ | ❌ | ❌ | ✅ |
| 长期晋升 | ❌ | ❌ | ❌ | ✅ |
| 记忆质量评估 | ❌ | ❌ | ❌ | ✅ **自动评分+清理** |
| 关联图谱 | ❌ | ❌ | ❌ | ✅ **因果/矛盾检测** |
| 智能相关性排序 | ⚠️ | ⚠️ | ⚠️ | ✅ **混合检索+重排序** |
| 本地优先 / 零重依赖核心 | ❌ | ❌ | ❌ | ✅ |
| 适合 Agent 工作流 | ⚠️ | ⚠️ | ⚠️ | ✅ **为 Agent 行为闭环设计** |

**一句话差异化定位：**

> DNA Memory 帮助 AI Agent 不只是“记住”，而是像人脑一样对信息进行强化、遗忘、归纳和进化。

---

## 🚀 30 秒快速开始

```bash
# 1) clone 到 OpenClaw skills 目录
git clone https://github.com/AIPMAndy/dna-memory.git ~/.openclaw/skills/dna-memory

# 2) 记录一条偏好
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py remember "用户喜欢简洁直接的回复" -t preference -i 0.9

# 3) 搜索记忆
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py recall "简洁 回复"

# 4) 查看统计
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py stats
```

**特点：**
- 核心功能只依赖 Python 标准库 + SQLite
- 不需要外部数据库
- 默认本地存储，适合个人 Agent / 本地 Agent / 自动化助手

---

## ✨ 核心能力

### 1. 三层记忆架构

```text
工作记忆（Working）
  ↓ 筛选
短期记忆（Short-term）
  ↓ 巩固 / 晋升
长期记忆（Long-term）
```

| 层级 | 作用 | 典型内容 |
|------|------|----------|
| 工作记忆 | 当前会话临时上下文 | 本轮任务、刚发生的事 |
| 短期记忆 | 近几天重要信息 | 用户偏好、近期经验、错误教训 |
| 长期记忆 | 稳定知识与模式 | 规则、技能、长期偏好、归纳后的 pattern |

### 2. 强化与遗忘

- **高频使用 → 权重提升**
- **长期不访问 → 权重衰减**
- **低权重记忆 → 可被清理**
- **被验证的高价值记忆 → 晋升为长期记忆**

### 3. Reflect 反思机制

`reflect` 会做两件事：
- 从近期高权重记忆里提炼高频模式
- 自动把稳定、重要的短期记忆晋升为长期记忆

### 4. Recall 搜索增强

当前版本已支持：
- **多关键词 AND 搜索**
- **`type:error` / `type:skill` 类型过滤**
- **SQLite FTS5 全文搜索**
- FTS5 不可用时自动回退 LIKE 搜索
- **🆕 智能相关性排序**（混合检索 + 多维度评分）
- **🆕 中文分词优化**（2-3 字切分 + 英文词提取）
- **🆕 上下文感知**（结合当前任务提升相关性）

示例：

```bash
# 基础 Recall
python3 scripts/evolve.py recall "飞书 API"
python3 scripts/evolve.py recall "type:error GitHub"

# 🆕 增强版 Recall（智能排序）
python3 scripts/advanced_recall.py "飞书 API" --context "正在调试消息发送"
python3 scripts/advanced_recall.py "错误" --type error --min-score 0.5
```

### 5. 后台自动维护（Daemon）

支持后台 daemon 定时执行：
- 自动 reflect
- 自动 decay
- 避免同一批记忆反复归纳

并可通过 **macOS launchd** 开机自启。

### 6. 🆕 记忆质量评估系统

自动评估记忆质量，识别高价值记忆和低质量记忆：
- **多维度评分**：访问频率、新鲜度、具体性、验证状态、关联度、重要性
- **质量等级**：excellent / good / fair / poor
- **自动清理**：清理低质量记忆，释放存储空间
- **健康度报告**：生成记忆系统健康度报告

```bash
# 评估所有记忆
python3 scripts/memory_quality.py evaluate --limit 20

# 生成健康度报告
python3 scripts/memory_quality.py report

# 清理低质量记忆（预览）
python3 scripts/memory_quality.py cleanup --threshold 0.2 --dry-run

# 实际清理
python3 scripts/memory_quality.py cleanup --threshold 0.2
```

### 7. 🆕 记忆关联图谱

自动发现记忆之间的关联关系：
- **关联类型**：相关、因果、矛盾、扩展、替代
- **自动发现**：基于文本相似度和语义分析
- **因果识别**：错误 → 解决方案
- **矛盾检测**：冲突的偏好自动标记
- **图谱可视化**：查看记忆关联网络

```bash
# 为单个记忆发现关联
python3 scripts/memory_graph.py discover --id 123

# 批量发现关联
python3 scripts/memory_graph.py batch --limit 100

# 查看记忆关联图谱
python3 scripts/memory_graph.py graph --id 123 --depth 2
```

---

## 📦 当前真实架构

```text
dna-memory/
├── scripts/
│   ├── evolve.py              # 核心 CLI：remember / recall / stats / reflect / dedupe ...
│   ├── dna_memory_daemon.py   # 后台守护：自动 reflect / decay
│   ├── semantic_search.py     # 语义搜索实验模块（可扩展）
│   ├── analyze.py
│   ├── api.py
│   ├── autocollect.py
│   ├── backup.py
│   ├── cli.py
│   ├── detailed_stats.py
│   ├── knowme_link.py
│   ├── reminder.py
│   ├── trigger.py
│   └── visualize.py
├── memory/
│   ├── memory.db              # SQLite 主库（记忆 + 操作日志）
│   └── working.json           # 工作记忆
├── assets/
│   └── config.json            # daemon/衰减等配置
├── README.md
├── README_EN.md
└── SKILL.md
```

> 注意：`memory/*.db` 不应提交到 Git，仓库已加入 ignore 保护真实记忆数据。

---

## 🧪 核心命令

### Remember

```bash
python3 scripts/evolve.py remember "Andy 喜欢简洁直接的回复" -t preference -i 0.95
```

### Recall

```bash
# 基础 Recall
python3 scripts/evolve.py recall "简洁 回复"
python3 scripts/evolve.py recall "type:skill 飞书"

# 增强版 Recall（智能搜索 + 上下文感知）
python3 scripts/enhanced_recall.py "关键词" --context "上下文"
python3 scripts/enhanced_recall.py --type error --limit 5
python3 scripts/enhanced_recall.py --recent 7
```

### Stats

```bash
python3 scripts/evolve.py stats
```

### Reflect

```bash
python3 scripts/evolve.py reflect
```

### Promote

```bash
python3 scripts/evolve.py promote --id 12
```

### Dedupe

```bash
python3 scripts/evolve.py dedupe
```

### Daemon

```bash
# 启动
python3 scripts/dna_memory_daemon.py start

# 查看状态
python3 scripts/dna_memory_daemon.py status

# 停止
python3 scripts/dna_memory_daemon.py stop
```

### SessionMemory（会话级记忆）

```bash
# 查看会话摘要
python3 scripts/session_memory.py summary

# 压缩会话记忆（token 使用 > 70% 时）
python3 scripts/session_memory.py compress

# 提取有价值的记忆（会话结束时）
python3 scripts/session_memory.py extract

# 清理会话记忆
python3 scripts/session_memory.py clear
```

### MemoryExtractor（自动记忆提取）

```bash
# 从对话日志中自动提取记忆
python3 scripts/memory_extractor.py --file conversation.json

# 只提取不写入（预览）
python3 scripts/memory_extractor.py --file conversation.json --dry-run

# 调整置信度阈值
python3 scripts/memory_extractor.py --file conversation.json --threshold 0.8
```

---

## ⚙️ 适用场景

### 1. 个人 AI 助理
- 记住用户偏好
- 逐步形成长期协作风格
- 从错误中学习，不重复犯错

### 2. Agent 工作流编排
- 任务执行后沉淀技能
- 失败案例进入 error memory
- 长任务形成模式归纳

### 3. AI 知识型产品
- 积累用户画像
- 记录行为模式
- 构建长期 personalization

### 4. 自我进化系统
- 配合 self-improving-agent / OpenClaw / 自定义 Agent 使用
- 把“经验”变成机器能持续复用的资产

---

## 🧭 推荐工作流

```text
收到任务
  ↓
Recall 相关记忆
  ↓
执行任务
  ↓
Remember 新偏好 / 新技能 / 错误
  ↓
Reflect 归纳模式
  ↓
Promote 到长期记忆
```

这套流程适合：
- 被用户纠正时
- 学到新偏好时
- 遇到 API 失败时
- 完成长任务时
- 发现重复模式时

---

## 🗺️ Roadmap

- [x] SQLite 单库重构
- [x] remember / recall / reflect / promote / dedupe CLI
- [x] daemon 自动 reflect / decay
- [x] recall 支持 FTS5 全文搜索
- [x] launchd 开机自启方案
- [x] 🆕 智能相关性排序（混合检索 + 多维度评分）
- [x] 🆕 中文分词优化（2-3 字切分）
- [x] 🆕 记忆质量评估系统（自动评分 + 清理）
- [x] 🆕 记忆关联图谱（因果/矛盾检测）
- [ ] 更强的中文分词（接入 jieba）
- [ ] 真正的 embedding 语义检索接入
- [ ] 记忆关联图谱可视化增强（Web UI）
- [ ] 更完整的导入 / 导出 / 迁移工具
- [ ] 多 Agent 共享记忆空间支持

---

## 🤝 贡献

欢迎提交 Issue / PR，一起把“AI 记忆”这件事做对。

建议优先贡献方向：
- recall 相关性排序
- 中文搜索体验
- pattern 抽取质量
- 记忆可视化
- 多模型 embedding 接入

---

## 👨‍💻 作者

**Andy / AI酋长Andy**  
前腾讯 / 百度 AI 产品专家 → 大模型独角兽 VP → 创业 CEO

关注方向：
- AI Agent
- AI 商业化
- 记忆系统
- 个体增强

GitHub: https://github.com/AIPMAndy

---

## 📄 License

[Apache 2.0](LICENSE)

---

<div align="center">

**如果这个项目对你有帮助，欢迎给个 ⭐ Star。**

</div>
