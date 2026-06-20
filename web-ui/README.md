# DNA Memory Web UI

DNA Memory 的 Web 可视化界面

## 功能

- 🏠 **首页**：功能介绍 + 实时统计预览
- 📅 **时间线**：按时间顺序展示所有记忆
- 📊 **统计面板**：可视化统计数据
- 🔗 **图谱**：记忆关联网络（开发中）

## 技术栈

- **框架**：Next.js 14 (App Router)
- **样式**：Tailwind CSS
- **数据库**：better-sqlite3 (只读模式)
- **可视化**：D3.js (图谱功能)
- **日期处理**：date-fns

## 安装

```bash
cd web-ui
npm install
```

## 运行

```bash
# 开发模式
npm run dev

# 访问
open http://localhost:3456
```

## API 端点

- `GET /api/stats` - 获取统计数据
- `GET /api/memories?limit=50&offset=0&type=preference` - 获取记忆列表

## 注意事项

- Web UI 以**只读模式**访问数据库，不会修改数据
- 数据库路径：`../memory/memory.db`（相对于 web-ui 目录）
- 端口：3456（避免与常见服务冲突）

## 构建

```bash
# 生产构建
npm run build

# 运行生产版本
npm start
```

## 目录结构

```
web-ui/
├── app/
│   ├── page.tsx              # 首页
│   ├── timeline/page.tsx     # 时间线
│   ├── stats/page.tsx        # 统计
│   ├── graph/page.tsx        # 图谱（开发中）
│   ├── layout.tsx            # 布局
│   ├── globals.css           # 全局样式
│   └── api/
│       ├── stats/route.ts    # 统计 API
│       └── memories/route.ts # 记忆列表 API
├── package.json
├── next.config.js
├── tsconfig.json
└── tailwind.config.js
```

## 集成到 Claude Code

可以通过 `.claude/launch.json` 配置一键启动：

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "dna-memory-web",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 3456,
      "cwd": "${workspaceFolder}/web-ui"
    }
  ]
}
```

然后在 Claude Code 中使用：
```
/run dna-memory-web
```
