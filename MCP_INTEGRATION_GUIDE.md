# DNA Memory MCP 集成指南

## ✅ 安装完成

DNA Memory 已成功配置为 Claude Code 的 MCP 服务器！

### 配置信息

**配置文件**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**服务器名称**: `dna-memory`

**Python**: `/opt/homebrew/opt/python@3.11/bin/python3.11`

**服务器路径**: `/Users/andy/Desktop/04 AICode/dna-memory-review/mcp-server/server.py`

**数据目录**: `/Users/andy/Desktop/04 AICode/dna-memory-review/memory`

---

## 🚀 启用步骤

### 1. 重启 Claude Desktop

**完全退出并重新启动 Claude Desktop**（必须完全退出，不是最小化）：

```bash
# 方法 1：从 Dock 右键退出
右键 Claude Desktop 图标 → 退出

# 方法 2：使用命令行
killall "Claude" && open -a "Claude"
```

### 2. 验证服务器已加载

重启后，在 Claude Code 中输入：

```
列出所有可用的 MCP 工具
```

你应该能看到 9 个 `dna_*` 工具。

---

## 🛠️ 可用工具（9个）

### 核心功能

| 工具 | 功能 | 示例 |
|------|------|------|
| `dna_remember` | 添加记忆 | "用 dna_remember 记录：用户偏好 TypeScript" |
| `dna_recall` | 搜索记忆 | "用 dna_recall 搜索 TypeScript 相关记忆" |
| `dna_stats` | 查看统计 | "用 dna_stats 显示记忆统计信息" |
| `dna_working_memory` | 操作工作记忆 | "用 dna_working_memory 查看当前工作记忆" |

### 高级功能

| 工具 | 功能 | 示例 |
|------|------|------|
| `dna_reflect` | 反思归纳 | "用 dna_reflect 归纳最近的模式" |
| `dna_decay` | 权重衰减 | "用 dna_decay 淡化旧记忆" |
| `dna_link` | 建立关联 | "用 dna_link 连接记忆 1 和记忆 2" |
| `dna_promote` | 晋升长期 | "用 dna_promote 将记忆 5 晋升到长期记忆" |
| `dna_forget` | 删除记忆 | "用 dna_forget 删除记忆 3" |

---

## 📊 资源（4个）

可以通过 "读取资源" 访问：

- `dna://stats/summary` - 实时统计信息
- `dna://working/current` - 当前工作记忆（最多7条）
- `dna://memories/recent` - 最近20条记忆
- `dna://memories/high-value` - 权重Top 20记忆

---

## 💡 使用示例

### 示例 1：记录用户偏好

```
用 dna_remember 添加记忆：
内容：用户喜欢用 Karpathy 四大原则编码
类型：preference
重要性：0.9
```

### 示例 2：搜索记忆

```
用 dna_recall 搜索 "Karpathy" 相关记忆
```

### 示例 3：查看统计

```
用 dna_stats 显示详细统计（detailed=true）
```

### 示例 4：反思归纳

```
用 dna_reflect 归纳高权重记忆中的模式
```

### 示例 5：查看工作记忆

```
用 dna_working_memory 执行 get 操作
```

---

## 🔧 工具参数详解

### dna_remember

```json
{
  "content": "记忆内容（必填）",
  "type": "fact|preference|skill|error|pattern|insight（默认fact）",
  "tags": "标签1,标签2（可选）",
  "importance": 0.6,  // 0-1之间，默认0.6
  "short_term": true,  // 是否放入短期记忆
  "long_term": false   // 是否直接长期记忆
}
```

### dna_recall

```json
{
  "query": "搜索关键词（支持 type:skill 过滤）",
  "limit": 10  // 返回数量，默认10，最大100
}
```

### dna_reflect

```json
{
  "min_weight": 0.7  // 参与反思的最低权重，默认0.7
}
```

### dna_decay

```json
{
  "factor": 0.95,       // 衰减因子，默认0.95（越接近1衰减越慢）
  "use_recency": true   // 是否使用访问敏感衰减
}
```

### dna_stats

```json
{
  "detailed": false  // 是否返回详细统计（类型分布等）
}
```

### dna_working_memory

```json
{
  "action": "add|get|clear",  // 操作类型
  "content": "内容（action=add时必填）",
  "importance": 0.8  // 重要性（仅用于add）
}
```

### dna_link

```json
{
  "memory_id1": 1,             // 第一个记忆ID
  "memory_id2": 2,             // 第二个记忆ID
  "relation_type": "related",  // 关系类型
  "weight": 0.5                // 关系强度
}
```

### dna_promote

```json
{
  "memory_id": 1  // 要晋升的记忆ID
}
```

### dna_forget

```json
{
  "memory_id": 1,      // 要删除的ID（可选）
  "threshold": 0.25    // 自动清理阈值（不填memory_id时使用）
}
```

---

## 🎯 工作流集成建议

### 1. 对话开始时

```
用 dna_working_memory 执行 get 操作，加载上次工作记忆
```

### 2. 对话过程中

```
# 自动记录重要洞察
用 dna_remember 记录关键发现

# 搜索相关历史
用 dna_recall 查找相关经验
```

### 3. 对话结束时

```
# 反思归纳
用 dna_reflect 提炼本次对话的模式

# 查看统计
用 dna_stats 查看记忆系统状态
```

### 4. 定期维护

```
# 每周执行一次
用 dna_decay 淡化不常用的记忆
用 dna_forget 清理低价值记忆（threshold=0.2）
```

---

## 🐛 故障排查

### 问题 1：工具不显示

**症状**：Claude Code 中看不到 `dna_*` 工具

**解决**：
1. 确认 Claude Desktop 已完全重启（不是最小化）
2. 检查配置文件：`cat ~/Library/Application\ Support/Claude/claude_desktop_config.json`
3. 查看 MCP 日志：`~/Library/Logs/Claude/mcp*.log`

### 问题 2：工具调用失败

**症状**：调用工具时报错

**解决**：
1. 测试服务器：`/opt/homebrew/opt/python@3.11/bin/python3.11 /Users/andy/Desktop/04\ AICode/dna-memory-review/mcp-server/server.py`
2. 检查数据库：`ls -lh /Users/andy/Desktop/04\ AICode/dna-memory-review/memory/memory.db`
3. 验证导入：`cd mcp-server && /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import handlers; print('OK')"`

### 问题 3：数据库锁定

**症状**：`database is locked` 错误

**解决**：
1. 停止后台 daemon：`python3 scripts/dna_memory_daemon.py stop`
2. 检查是否有其他进程在使用：`lsof /Users/andy/Desktop/04\ AICode/dna-memory-review/memory/memory.db`

---

## 📚 技术细节

### 架构

```
Claude Code
    ↓ (MCP 协议)
server.py (MCP 适配层)
    ↓ (函数调用)
handlers.py (参数适配)
    ↓ (复用逻辑)
evolve.py (业务逻辑)
    ↓ (SQLite)
memory.db (数据存储)
```

### 零代码重复

MCP 服务器**完全复用** `evolve.py` 的功能，没有重写任何业务逻辑。

### 性能

- **启动时间**: < 100ms
- **响应时间**: < 50ms（简单查询）
- **并发安全**: 使用 fcntl 文件锁
- **容量**: 最多 10000 条记忆

---

## 🔐 安全性

- ✅ SQL 注入防护（输入清理+参数化查询）
- ✅ 容量限制（硬上限 10000 条）
- ✅ 并发控制（事务管理+文件锁）
- ✅ 备份机制（自动备份+7天保留）
- ✅ 权限隔离（仅访问指定数据目录）

---

## 📦 文件清单

```
dna-memory-review/
├── mcp-server/
│   ├── server.py              # MCP 主服务器
│   ├── handlers.py            # 工具处理器
│   ├── config.py              # 配置管理
│   ├── requirements.txt       # Python 依赖
│   ├── README.md              # 详细文档
│   ├── install.sh             # 自动安装脚本
│   └── IMPLEMENTATION_SUMMARY.md
├── scripts/
│   ├── evolve.py              # 核心业务逻辑
│   ├── backup.py              # 备份恢复
│   ├── memory_distillation.py # 记忆蒸馏
│   └── dna_memory_daemon.py   # 后台守护
├── memory/
│   ├── memory.db              # SQLite 数据库
│   ├── working.json           # 工作记忆
│   └── backups/               # 自动备份
└── MCP_INTEGRATION_GUIDE.md   # 本文档
```

---

## 🎉 现在可以用了！

**重启 Claude Desktop，然后在对话中输入：**

```
用 dna_stats 显示记忆统计
```

如果看到统计信息输出，说明集成成功！🎊

---

**文档版本**: 1.0  
**最后更新**: 2026-06-17  
**项目地址**: https://github.com/AIPMAndy/dna-memory
