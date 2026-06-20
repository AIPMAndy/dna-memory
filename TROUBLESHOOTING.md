# 故障排查指南

## 常见问题

### 1. Python 版本问题

**问题**: `pip3 install mcp` 报错或 MCP 服务器无法启动

**原因**: MCP SDK 需要 Python 3.10+，但系统 Python 是 3.9 或更低

**解决方案**:

```bash
# 检查 Python 版本
python3 --version

# macOS 用户：安装 Python 3.11
brew install python@3.11

# 使用特定版本
python3.11 -m pip install mcp
python3.11 scripts/evolve.py stats

# 或者更新 mcp-server/server.py 第一行的 shebang
# 改为你的 Python 3.10+ 路径
which python3.11  # 找到路径
# 然后修改 server.py 第一行
```

---

### 2. Web UI 无法启动

**问题**: `npm run dev` 报错

**解决方案**:

```bash
# 检查 Node.js 版本（需要 16+）
node --version

# 如果版本太低，更新 Node.js
# macOS: brew install node
# 或访问 https://nodejs.org/

# 清理并重新安装依赖
cd web-ui
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

### 3. 数据库锁定错误

**问题**: `sqlite3.OperationalError: database is locked`

**原因**: 多个进程同时访问数据库

**解决方案**:

```bash
# 1. 关闭所有运行中的 DNA Memory 进程
pkill -f "evolve.py"
pkill -f "auto_memory_collector.py"
pkill -f "dna_memory_daemon.py"

# 2. 检查是否有进程占用数据库
lsof memory/memory.db

# 3. 如果问题持续，备份并重建数据库
mv memory/memory.db memory/memory.db.backup
python3 scripts/evolve.py stats  # 会自动创建新数据库
```

---

### 4. MCP 服务器无法连接

**问题**: Claude Code 中看不到 DNA Memory 工具

**解决方案**:

```bash
# 1. 检查 MCP 配置文件
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 应该包含类似内容：
# {
#   "mcpServers": {
#     "dna-memory": {
#       "command": "/path/to/python3",
#       "args": ["/path/to/dna-memory/mcp-server/server.py"]
#     }
#   }
# }

# 2. 手动测试 MCP 服务器
cd mcp-server
python3 server.py  # 应该没有报错

# 3. 重启 Claude Desktop
# Command+Q 完全退出，然后重新打开

# 4. 查看 MCP 日志
tail -f ~/Library/Logs/Claude/mcp*.log
```

---

### 5. Web UI 显示空数据

**问题**: 打开 Web UI 但看不到任何记忆

**原因**: 数据库为空或路径不正确

**解决方案**:

```bash
# 1. 检查数据库是否存在
ls -lh memory/memory.db

# 2. 检查数据库内容
python3 scripts/evolve.py stats

# 3. 如果数据库为空，添加一些测试数据
python3 scripts/auto_memory_collector.py

# 4. 刷新浏览器
```

---

### 6. 自动采集器没有反应

**问题**: 运行 `auto_memory_collector.py` 但没有输出

**解决方案**:

```bash
# 1. 检查是否正常运行（应该看到测试输出）
python3 scripts/auto_memory_collector.py

# 2. 如果没有输出，检查日志级别
# 编辑 auto_memory_collector.py，确保 logging.basicConfig 的 level=logging.DEBUG

# 3. 手动测试采集逻辑
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from auto_memory_collector import AutoMemoryCollector
collector = AutoMemoryCollector()
result = collector.process_message('我喜欢用 TypeScript')
print(f'Result: {result}')
"
```

---

### 7. 端口占用

**问题**: Web UI 启动失败，提示端口 3456 已被占用

**解决方案**:

```bash
# 1. 查找占用端口的进程
lsof -i :3456

# 2. 杀死进程（替换 PID）
kill -9 <PID>

# 或者使用不同端口
cd web-ui
npm run dev -- -p 3000  # 使用 3000 端口
```

---

### 8. 性能问题

**问题**: 搜索或写入很慢

**解决方案**:

```bash
# 1. 检查数据库大小
ls -lh memory/memory.db

# 2. 重建 FTS5 索引
python3 -c "
import sys
sys.path.insert(0, 'scripts')
import evolve
evolve.init_db()  # 会重建索引
"

# 3. 如果数据库过大（>100MB），考虑清理低权重记忆
python3 scripts/evolve.py forget --threshold 0.3
```

---

## 获取帮助

### 查看详细日志

```bash
# 开启调试模式
export DNA_MEMORY_DEBUG=1

# 运行命令时会看到详细日志
python3 scripts/evolve.py recall "keyword"
```

### 验证安装

```bash
# 运行完整检查脚本
./scripts/release_check.sh

# 应该看到所有核心功能的 ✅ 标记
```

### 提交 Issue

如果以上方法都无法解决问题：

1. 访问 https://github.com/AIPMAndy/dna-memory/issues
2. 提供以下信息：
   - 操作系统版本
   - Python 版本 (`python3 --version`)
   - Node.js 版本 (`node --version`)
   - 完整错误信息
   - 复现步骤

---

## 重置到初始状态

如果一切都不工作，完全重置：

```bash
# 1. 备份重要数据
cp memory/memory.db memory/memory.db.backup

# 2. 清理所有生成文件
rm -rf memory/memory.db
rm -rf web-ui/node_modules
rm -rf web-ui/.next

# 3. 重新开始
python3 scripts/evolve.py stats  # 初始化数据库
cd web-ui && npm install  # 重新安装依赖
```

---

**最后更新**: 2026-06-18  
**版本**: v3.0
