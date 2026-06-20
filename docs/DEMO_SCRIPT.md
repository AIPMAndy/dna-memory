# DNA Memory 30 秒 Demo 脚本

## 🎬 视频脚本（30 秒）

### 场景 1: 问题场景（5 秒）
**画面**: 打开 ChatGPT/Claude，展示零散的对话历史
**旁白**: "你的 AI 总是忘记上次说过什么？"

### 场景 2: 解决方案（10 秒）
**画面**: DNA Memory Web UI 时间线视图
**旁白**: "DNA Memory 让 AI 像人脑一样记忆。零配置，自动学习你的偏好、决策和知识。"

**画面切换**:
- 显示自动采集的记忆（"用户喜欢 TypeScript"）
- 显示统计面板（158 条记忆，0.5ms 性能）
- 显示关系图谱（可视化）

### 场景 3: 核心价值（10 秒）
**画面**: 对比表格
**旁白**: "比 Mem0 快 100 倍，免费开源，本地优先。"

**显示特性**:
- ✅ 零配置自动采集
- ✅ 0.5ms 超快性能
- ✅ Web 可视化界面

### 场景 4: 行动召唤（5 秒）
**画面**: GitHub Star 按钮 + 安装命令
**旁白**: "3 行命令，5 秒上手。"

```bash
git clone https://github.com/AIPMAndy/dna-memory.git
cd dna-memory && python3 scripts/auto_memory_collector.py
cd web-ui && npm install && npm run dev
```

**结束画面**: "给个 Star ⭐，让 AI 记住你"

---

## 📸 截图清单

### 必需截图（7 张）

#### 1. Web UI 首页
**文件名**: `screenshot-home.png`
**内容**:
- 顶部导航栏（Logo + 菜单）
- 核心功能介绍卡片（自动采集、Web 界面、超快性能）
- 实时统计预览（记忆总数、短期/长期分布）

**展示要点**:
- 界面简洁清爽
- 核心价值一目了然

---

#### 2. 时间线视图
**文件名**: `screenshot-timeline.png`
**内容**:
- 时间线列表（10-15 条记忆）
- 记忆卡片（显示类型、重要性、时间戳）
- 搜索框和过滤器

**展示要点**:
- 记忆按时间排列
- 不同类型有不同颜色标识
- 可搜索可过滤

---

#### 3. 统计面板
**文件名**: `screenshot-stats.png`
**内容**:
- 总览卡片（总数、平均权重、短期/长期占比）
- 类型分布图（偏好、决策、错误、知识）
- 操作记录表格（最近 10 条操作）

**展示要点**:
- 数据可视化清晰
- 统计维度丰富

---

#### 4. 自动采集测试
**文件名**: `screenshot-auto-collector.png`
**内容**:
- 终端界面运行 `python3 scripts/auto_memory_collector.py`
- 输入示例："我喜欢用 TypeScript 而不是 JavaScript"
- 输出结果："✅ Collected (ID=10, score=0.92)"
- 输入噪音："好的"
- 输出结果："⏭️ Skipped (噪音过滤)"

**展示要点**:
- 自动识别有效内容
- 正确过滤噪音
- 实时反馈清晰

---

#### 5. MCP 工具列表
**文件名**: `screenshot-mcp-tools.png`
**内容**:
- Claude Code 中调用 `dna_remember`
- 显示 10 个 MCP 工具列表
- 突出显示新增的 `dna_auto_collect` 工具

**展示要点**:
- Claude Code 原生集成
- 工具丰富完整

---

#### 6. 性能对比表
**文件名**: `screenshot-performance.png`
**内容**:
- 对比表格（DNA Memory vs Mem0 vs Zep）
- 突出显示性能优势（0.5ms vs 50ms）
- 标注"快 100 倍"

**展示要点**:
- 数据真实可信
- 优势一目了然

---

#### 7. 架构图
**文件名**: `screenshot-architecture.png`
**内容**:
- 三层记忆架构示意图
- 自动采集流程图
- 技术栈说明

**展示要点**:
- 技术实现清晰
- 架构设计合理

---

## 🎥 录屏要点（可选）

### 完整演示流程（2-3 分钟）

#### Part 1: 安装与启动（30 秒）
1. 克隆仓库
2. 测试自动采集器
3. 启动 Web UI

#### Part 2: 自动采集演示（60 秒）
1. 运行 `auto_memory_collector.py`
2. 输入多种类型的对话：
   - "我喜欢用 FastAPI 构建 API"（偏好）
   - "决定使用 PostgreSQL 作为数据库"（决策）
   - "遇到数据库锁定错误，改用单一事务解决了"（错误）
   - "原来 Python 3.11 比 3.9 快 20%"（知识）
   - "好的"、"继续"（噪音，应被过滤）
3. 展示采集结果

#### Part 3: Web UI 浏览（60 秒）
1. 打开首页，浏览功能介绍
2. 进入时间线视图，展示记忆列表
3. 搜索功能演示（输入"TypeScript"）
4. 统计面板，展示数据可视化
5. 展示类型分布图

#### Part 4: MCP 集成演示（30 秒）
1. 打开 Claude Code
2. 调用 `dna_remember` 添加记忆
3. 调用 `dna_recall` 搜索记忆
4. 调用 `dna_auto_collect` 查看状态

---

## 📝 截图规范

### 技术要求
- **分辨率**: 1920x1080 或更高
- **格式**: PNG（支持透明背景）
- **文件大小**: 单张 < 500KB（优化压缩）
- **命名**: `screenshot-{功能名}.png`

### 视觉要求
- **浏览器**: 使用 Chrome，隐藏书签栏
- **终端**: 使用 iTerm2 或 Warp，选择简洁主题
- **窗口**: 全屏或固定尺寸（避免不规则边框）
- **字体**: 确保代码清晰可读
- **示例数据**: 使用真实但脱敏的数据

### 美化要点
- 使用浏览器开发者工具调整颜色对比度
- 截图前清理控制台输出
- 确保没有个人敏感信息（API key、路径等）
- 可使用标注工具添加箭头/高亮（可选）

---

## 🎨 GIF 动画（可选）

### 推荐工具
- **macOS**: Kap (https://getkap.co/)
- **跨平台**: ScreenToGif

### 动画场景
1. **自动采集过程**（5 秒）
   - 输入文本 → 实时显示采集结果 → 过滤噪音

2. **Web UI 交互**（8 秒）
   - 首页 → 点击时间线 → 搜索记忆 → 展示结果

3. **性能展示**（3 秒）
   - 运行性能测试 → 显示 0.5ms 结果

### GIF 规范
- **帧率**: 15-20 fps
- **分辨率**: 1280x720
- **文件大小**: < 5MB
- **循环**: 无限循环
- **时长**: 3-10 秒

---

## 📦 素材存放

```
dna-memory/
├── docs/
│   ├── screenshots/
│   │   ├── screenshot-home.png
│   │   ├── screenshot-timeline.png
│   │   ├── screenshot-stats.png
│   │   ├── screenshot-auto-collector.png
│   │   ├── screenshot-mcp-tools.png
│   │   ├── screenshot-performance.png
│   │   └── screenshot-architecture.png
│   └── demos/
│       ├── auto-collection.gif
│       ├── web-ui-interaction.gif
│       └── full-demo.mp4
└── README.md  # 引用截图
```

---

## 🚀 使用说明

### 在 README 中引用
```markdown
<div align="center">
<img src="./docs/screenshots/screenshot-home.png" alt="Web UI Homepage" />
</div>

### 自动采集演示
![Auto Collection Demo](./docs/demos/auto-collection.gif)
```

### 在 Product Hunt 中使用
- 首图：`screenshot-home.png`（1270x760）
- Gallery：其余 6 张截图
- Demo 视频：`full-demo.mp4`（< 1 分钟）

---

## ✅ 检查清单

制作完成后，确认：
- [ ] 所有 7 张截图已完成
- [ ] 截图质量清晰，无模糊
- [ ] 无个人敏感信息泄露
- [ ] 文件大小符合要求
- [ ] 命名规范统一
- [ ] 已更新到 README.md
- [ ] 已添加到 GitHub 仓库
- [ ] （可选）GIF 动画制作完成

---

**制作人**: Andy  
**日期**: 2026-06-18  
**版本**: v1.0
