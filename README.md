<div align="center">

# 🧬 DNA Memory

**让 AI 像人脑一样记忆与进化**  
零配置自动采集 · 智能可视化 · 超快性能

[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-3.0-green)](https://github.com/AIPMAndy/dna-memory/releases)

[English](./README_EN.md) | **简体中文** | [性能报告](./docs/performance_report.md) | [架构设计](./docs/auto_collector_architecture.md)

</div>

---

## 💡 核心价值

> 大多数 AI 记忆系统只是在"存储"。  
> **DNA Memory 让 AI 真正"学习"** —— 自动采集对话、智能强化、主动遗忘、归纳进化。

### 🎯 三大突破

1. **🤖 零配置自动采集** — 无需手动记录，AI 自动识别你的偏好、决策和知识
2. **📊 Web 可视化界面** — 时间线、统计图表、关系图谱，一目了然
3. **⚡ 超快性能** — 0.5ms 采集延迟，用户无感知

---

## 🚀 快速开始

### 前置要求
- Python 3.8+ （推荐 3.10+）
- Node.js 16+ （用于 Web UI）

### 一键验证

```bash
# 克隆并验证
git clone https://github.com/AIPMAndy/dna-memory.git
cd dna-memory
./scripts/quick_verify.sh

# 如果看到 "✅ 所有核心功能验证通过！"，说明安装成功
```

### 方式一：快速测试（2 分钟）

```bash
# 1. 克隆项目
git clone https://github.com/AIPMAndy/dna-memory.git
cd dna-memory

# 2. 测试自动采集（会自动初始化数据库）
python3 scripts/auto_memory_collector.py

# 你会看到测试输出：
# Input: 我喜欢用 TypeScript 而不是 JavaScript
# Result: ✅ Collected
# ...
```

### 方式二：完整体验（5 分钟）

```bash
# 1. 手动记录一条记忆
python3 scripts/evolve.py remember "用户喜欢简洁直接的回复" -t preference -i 0.9

# 2. 搜索记忆
python3 scripts/evolve.py recall "简洁"

# 3. 查看统计
python3 scripts/evolve.py stats

# 4. 启动 Web UI（首次需要安装依赖，约 1-2 分钟）
cd web-ui && npm install && npm run dev
# 访问 http://localhost:3456
```

---

## ✨ 核心功能

### 🤖 自动记忆采集（🔥 新功能）

**无需手动记录，AI 自动学习你的习惯**

```python
# 你说："我喜欢用 TypeScript 而不是 JavaScript"
# AI 自动记录：
{
  "type": "preference",
  "content": "我喜欢用 TypeScript 而不是 JavaScript",
  "importance": 0.92,
  "layer": "短期"
}
```

**智能识别 4 类内容：**
- ✅ 偏好声明（"我喜欢..."、"我习惯..."）
- ✅ 决策记录（"决定用..."、"选择..."）
- ✅ 错误教训（"遇到 XX 错误，YY 解决"）
- ✅ 知识发现（"原来..."、"发现..."）

**性能数据：**
- 处理速度：**0.54ms/条**（用户无感知）
- 过滤准确率：**100%**（自动过滤"好的"、"继续"等噪音）
- 去重检查：**编辑距离 80% 阈值**

---

### 📊 Web 可视化界面（🔥 新功能）

**告别命令行，用浏览器管理你的记忆**

<div align="center">
<img src="./docs/screenshots/screenshot-home.png" alt="DNA Memory Web UI" />
<p><i>↑ DNA Memory Web UI 界面预览（<a href="./docs/DEMO_SCRIPT.md">查看完整 Demo</a>）</i></p>
</div>

**功能亮点：**
- 🏠 **首页**：功能介绍 + 实时统计
- 📅 **时间线**：按时间展示所有记忆
- 📊 **统计面板**：类型分布、容量使用、操作记录
- 🔗 **关系图谱**：可视化记忆关联（开发中）

```bash
cd web-ui
npm install
npm run dev
# 访问 http://localhost:3456
```

---

### 🧠 三层记忆架构

```text
工作记忆 (7 条)
  ↓ 筛选
短期记忆 (< 1000 条)
  ↓ 晋升
长期记忆 (< 5000 条)
```

| 层级 | 作用 | 典型内容 |
|------|------|----------|
| 工作记忆 | 当前会话临时上下文 | 本轮任务、刚发生的事 |
| 短期记忆 | 近期重要信息 | 用户偏好、错误教训 |
| 长期记忆 | 稳定知识与模式 | 规则、技能、归纳模式 |

---

### ⚡ 超快性能

| 指标 | 性能 | 对比 Mem0 | 状态 |
|------|------|-----------|------|
| 写入速度 | **0.47ms/条** | 快 100x | ✅ |
| 搜索速度 | **< 5ms** | 快 20x | ✅ |
| 自动采集 | **0.54ms/条** | N/A | ✅ |
| 内存占用 | **< 10MB** | 小 10x | ✅ |

**完整性能报告** → [performance_report.md](./docs/performance_report.md)

---

## 🎯 使用场景

### 1. 个人 AI 助理
- ✅ 自动记住你的编码风格偏好
- ✅ 从错误中学习，不重复犯错
- ✅ 逐步形成长期协作风格

### 2. Agent 开发
- ✅ 任务执行后自动沉淀技能
- ✅ 失败案例自动进入 error memory
- ✅ 长任务自动形成模式归纳

### 3. 知识管理
- ✅ 自动提取对话中的知识点
- ✅ 可视化知识图谱
- ✅ 智能搜索快速定位

---

## 🚀 快速开始

### 方式一：Claude Code MCP 服务器（🔥 推荐）

让 Claude Code 直接调用 DNA Memory！

**前置要求**：Python 3.10+（检查：`python3 --version`）

```bash
# 1. 克隆项目
git clone https://github.com/AIPMAndy/dna-memory.git

# 2. 检查 Python 版本
python3 --version  # 需要 3.10 或更高

# 如果版本低于 3.10，macOS 用户可以：
# brew install python@3.11
# 然后使用 python3.11 替代 python3

# 3. 安装 MCP SDK
pip3 install mcp

# 4. 运行自动安装（会配置 Claude Desktop）
cd dna-memory/mcp-server && ./install.sh

# 5. 重启 Claude Desktop

# 6. 在 Claude Code 中使用
"用 dna_remember 记录：用户喜欢简洁直接的回复"
"用 dna_auto_collect 执行 enable 操作"
"用 dna_stats 显示统计"
```

**10 个 MCP 工具：**
- `dna_remember` - 添加记忆
- `dna_recall` - 搜索记忆
- `dna_auto_collect` - 控制自动采集（🔥 新增）
- `dna_stats` - 查看统计
- `dna_reflect` - 反思归纳
- `dna_decay` - 权重衰减
- `dna_promote` - 晋升长期
- `dna_link` - 建立关联
- `dna_forget` - 删除记忆
- `dna_working_memory` - 工作记忆

**详细指南** → [MCP_INTEGRATION_GUIDE.md](./MCP_INTEGRATION_GUIDE.md)  
**故障排查** → [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

### 方式二：独立使用

```bash
# 1. 克隆项目
git clone https://github.com/AIPMAndy/dna-memory.git
cd dna-memory

# 2. 记录一条偏好
python3 scripts/evolve.py remember "用户喜欢简洁直接的回复" -t preference -i 0.9

# 3. 搜索记忆
python3 scripts/evolve.py recall "简洁 回复"

# 4. 查看统计
python3 scripts/evolve.py stats

# 5. 启动 Web UI
cd web-ui && npm install && npm run dev
```

---

### 方式三：自动采集测试

```bash
# 运行测试脚本（会自动初始化数据库）
python3 scripts/auto_memory_collector.py

# 你会看到自动测试输出：
# Input: 我喜欢用 TypeScript 而不是 JavaScript
# Result: ✅ Collected (ID=10, score=0.92)
# 
# Input: 遇到数据库锁定错误，修改为单一事务解决了
# Result: ✅ Collected (ID=12, score=0.90, type=error)
# 
# Input: 好的
# Result: ⏭️ Skipped (噪音过滤)

# 测试完成后，查看采集的记忆：
python3 scripts/evolve.py recall "TypeScript"
```

---

## 🆚 为什么选择 DNA Memory？

| 能力 | Mem0 | Zep | LangChain | **DNA Memory** |
|------|:----:|:---:|:---------:|:--------------:|
| **🔥 自动采集** | ❌ | ❌ | ❌ | ✅ **零配置** |
| **🔥 Web 界面** | ⚠️ 付费 | ⚠️ 付费 | ❌ | ✅ **免费开源** |
| **⚡ 性能** | 50ms | 20ms | 10ms | ✅ **0.5ms** |
| 三层架构 | ❌ | ⚠️ | ❌ | ✅ |
| 主动遗忘 | ❌ | ❌ | ❌ | ✅ |
| 自动反思 | ❌ | ❌ | ❌ | ✅ |
| MCP 集成 | ❌ | ❌ | ❌ | ✅ |
| 本地优先 | ❌ | ❌ | ❌ | ✅ |
| 零依赖核心 | ❌ | ❌ | ❌ | ✅ |

**性能对比基于真实测试数据**（详见 [performance_report.md](./docs/performance_report.md)）

---

## 📦 架构设计

```text
dna-memory/
├── scripts/
│   ├── evolve.py                  # 核心 CLI
│   ├── auto_memory_collector.py   # 🔥 自动采集器
│   └── dna_memory_daemon.py       # 后台守护
├── mcp-server/
│   ├── server.py                  # MCP 服务器
│   ├── hooks.py                   # 🔥 消息监听钩子
│   └── handlers.py                # 工具处理器
├── web-ui/                        # 🔥 Next.js Web UI
│   ├── app/
│   │   ├── page.tsx               # 首页
│   │   ├── timeline/page.tsx      # 时间线
│   │   ├── stats/page.tsx         # 统计
│   │   └── api/                   # API 端点
│   └── package.json
├── memory/
│   └── memory.db                  # SQLite 数据库
└── docs/
    ├── auto_collector_architecture.md  # 架构设计
    └── performance_report.md           # 性能报告
```

---

## 🧪 核心命令

### 基础操作
```bash
# 记录记忆
python3 scripts/evolve.py remember "内容" -t preference -i 0.9

# 搜索记忆
python3 scripts/evolve.py recall "关键词"

# 查看统计
python3 scripts/evolve.py stats

# 反思归纳
python3 scripts/evolve.py reflect

# 启动后台维护
python3 scripts/dna_memory_daemon.py start
```

### 自动采集
```bash
# 测试自动采集器
python3 scripts/auto_memory_collector.py

# 在 Claude Code 中控制
dna_auto_collect --action enable   # 启用
dna_auto_collect --action disable  # 禁用
dna_auto_collect --action status   # 状态
```

---

## 🛠️ 技术栈

**核心（零依赖）：**
- Python 3.8+
- SQLite（Python 标准库）

**可选功能：**
- MCP SDK → `pip install mcp`
- Web UI → Next.js 14 + Tailwind CSS
- 测试 → `pip install pytest`

**特点：**
- ✅ 本地优先存储
- ✅ 零外部依赖核心
- ✅ 适合个人/本地 Agent

---

## 📊 性能数据

基于真实测试（162 条记忆，详见 [performance_report.md](./docs/performance_report.md)）：

| 操作 | 性能 | 数据规模 |
|------|------|----------|
| 写入记忆 | 0.47ms/条 | 100 条 |
| 搜索记忆 | 1.48ms | 50 条结果 |
| 自动采集 | 0.54ms/条 | 60 条消息 |
| 统计计算 | 0.23ms | 162 条 |
| 数据库大小 | 136KB | 162 条 |

**预估 10000 条记忆：**
- 写入时间：~5s
- 搜索时间：< 10ms
- 数据库大小：~8.6MB

---

## 🗺️ Roadmap

### ✅ Phase 1 (已完成)
- [x] SQLite 单库重构
- [x] 三层记忆架构
- [x] FTS5 全文搜索
- [x] MCP 服务器集成
- [x] 🔥 自动采集器
- [x] 🔥 Web UI 可视化
- [x] 🔥 性能优化

### 🔜 Phase 2 (计划中)
- [ ] D3.js 关系图谱可视化
- [ ] 一键分享功能
- [ ] Chrome/VSCode 插件
- [ ] 语义搜索（embedding）
- [ ] 多 Agent 共享记忆

### 💡 Phase 3 (未来)
- [ ] 开放 API
- [ ] 插件市场
- [ ] 云端同步（可选）
- [ ] 移动端应用

---

## 🤝 贡献

欢迎提交 Issue / PR，一起让 AI 记忆更智能！

**优先贡献方向：**
- 🔥 自动采集规则优化
- 📊 Web UI 功能增强
- 🌐 浏览器插件开发
- 📝 文档/教程完善
- 🎨 UI/UX 设计改进

---

## 👨‍💻 作者

**Andy / AI酋长Andy**  
前腾讯/百度 AI 产品专家 → 大模型独角兽 VP → 创业 CEO

关注方向：
- AI Agent
- 记忆系统
- 个体增强

GitHub: https://github.com/AIPMAndy

---

## 📄 License

[Apache 2.0](LICENSE)

---

<div align="center">

**如果这个项目对你有帮助，欢迎给个 ⭐ Star！**

**v3.0 让 AI 记忆真正"活"起来。**

[⭐ Star on GitHub](https://github.com/AIPMAndy/dna-memory) | [📖 文档](./docs/) | [💬 讨论](https://github.com/AIPMAndy/dna-memory/discussions)

</div>
