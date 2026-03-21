# 🧬 DNA Memory

[English](./README_EN.md) | 中文

> 让 AI Agent 像人脑一样学习和成长

[![Star](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=flat)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![OpenClaw](https://img.shields.io/badge/Built%20for-OpenClaw-purple)](https://github.com/openclaw/openclaw)

---

## 🚀 快速开始

```bash
# 安装
pip install dna-memory

# 使用
python -m dna_memory remember "我喜欢简洁的回复" -t preference
python -m dna_memory recall "偏好"
python -m dna_memory stats
```

---

## 📺 Demo 演示

```bash
$ cd ~/.openclaw/skills/dna-memory

# 记录重要偏好
$ python3 scripts/evolve.py remember "我喜欢简洁的回复" -t preference -i 0.9
✅ 已记录记忆: 我喜欢简洁的回复 [偏好: 0.9]

# 查看工作记忆
$ python3 scripts/evolve.py working
📌 工作记忆 (3/7 条):
   1. Andy 喜欢简洁的回复 [⭐0.9]
   2. 沟通风格: 直接高效 [⭐0.8]

# 语义搜索相似记忆
$ python3 scripts/semantic_search.py search "编程"
   [0.92] 会用 Python 写 CLI 工具
   [0.87] 擅长 JavaScript 开发

# 详细统计
$ python3 scripts/detailed_stats.py
========================================
🧬 DNA Memory 统计报告
========================================

📊 总量统计:
   总记忆: 363 条
   短期记忆: 100 条
   长期记忆: 263 条

⚖️ 权重分布:
   平均权重: 0.65
   高权重(≥0.8): 45 条
   低权重(<0.3): 12 条 ⚠️
```

---

## 🧠 核心特性

### 三层记忆架构

| 层级 | 容量 | 遗忘周期 | 用途 |
|------|------|----------|------|
| 工作记忆 | 5-7 条 | 即时 | 当前对话关键信息 |
| 短期记忆 | 100 条 | 7天 | 用户偏好/习惯 |
| 长期记忆 | ∞ | 智能 | 核心技能/知识 |

### 智能遗忘机制

- **权重衰减**：信息随着时间推移自动降低权重
- **Relevance Filter**：只保留高相关性记忆
- **自动清理**：权重低于 0.25 自动删除

### 语义搜索

- 基于 Embeddings 的相似记忆搜索
- 支持 OpenAI text-embedding-3-small
- 本地 hash 备用方案

---

## 📁 项目结构

```
dna-memory/
├── scripts/           # 命令行工具
│   ├── evolve.py     # 主程序：记忆存取
│   ├── reflect.py    # LLM 模式归纳
│   ├── autocollect.py # 自动采集对话
│   ├── semantic_search.py # 语义搜索
│   ├── backup.py     # 导出/导入备份
│   ├── detailed_stats.py # 详细统计
│   └── knowme_link.py # KnowMe 联动
├── memory/           # 记忆存储
│   ├── short_term.db    # 短期记忆
│   ├── long_term.db    # 长期记忆
│   ├── working.json    # 工作记忆
│   └── embeddings.json # 语义向量
└── tests/            # 测试用例
```

---

## 🔧 配置选项

```python
from dna_memory import Memory

memory = Memory(
    short_term_capacity=100,    # 短期记忆容量
    long_term_capacity=-1,     # 长期记忆无限
    forget_threshold=0.3,       # 遗忘阈值
    relevance_weight=0.7,       # 相关性权重
)
```

---

## 🤖 自动化 (Cron)

每日凌晨自动执行：

| 时间 | 任务 |
|------|------|
| 02:00 | decay → link → autocollect → reflect → build embeddings → stats |
| 03:00 (周日) | backup export |

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## 📄 License

Apache 2.0 License - 随意使用，保留署名即可

---

## 👤 作者

**Andy** - [GitHub](https://github.com/AIPMAndy)

> 让 AI 成为真正的伙伴，而不是每次都要重新介绍的陌生人。
