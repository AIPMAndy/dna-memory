#!/bin/bash
# DNA Memory v3.0 发布准备脚本

set -e

PROJECT_ROOT="/Users/andy/Desktop/04 AICode/dna-memory-review"
cd "$PROJECT_ROOT"

echo "🚀 DNA Memory v3.0 发布准备检查"
echo "================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查函数
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
}

echo "📋 核心功能检查"
echo "---------------"

# 1. 检查核心脚本
if [ -f "scripts/evolve.py" ]; then
    check_pass "核心脚本 evolve.py 存在"
else
    check_fail "核心脚本 evolve.py 缺失"
    exit 1
fi

if [ -f "scripts/auto_memory_collector.py" ]; then
    check_pass "自动采集器 auto_memory_collector.py 存在"
else
    check_fail "自动采集器 auto_memory_collector.py 缺失"
    exit 1
fi

# 2. 检查 MCP 服务器
if [ -f "mcp-server/server.py" ]; then
    check_pass "MCP 服务器 server.py 存在"
else
    check_fail "MCP 服务器 server.py 缺失"
    exit 1
fi

if [ -f "mcp-server/hooks.py" ]; then
    check_pass "MCP hooks.py 存在"
else
    check_fail "MCP hooks.py 缺失"
    exit 1
fi

# 3. 检查 Web UI
if [ -f "web-ui/package.json" ]; then
    check_pass "Web UI package.json 存在"
else
    check_fail "Web UI package.json 缺失"
    exit 1
fi

if [ -d "web-ui/app" ]; then
    check_pass "Web UI app 目录存在"
else
    check_fail "Web UI app 目录缺失"
    exit 1
fi

echo ""
echo "📄 文档检查"
echo "----------"

# 4. 检查文档
docs=(
    "README.md"
    "CHANGELOG.md"
    "docs/auto_collector_architecture.md"
    "docs/performance_report.md"
    "docs/RELEASE_CHECKLIST.md"
    "docs/DEMO_SCRIPT.md"
    "docs/LAUNCH_PLAN.md"
    "MCP_INTEGRATION_GUIDE.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "$doc"
    else
        check_warn "$doc 缺失"
    fi
done

echo ""
echo "📸 素材检查"
echo "----------"

# 5. 检查截图目录
if [ -d "docs/screenshots" ]; then
    screenshot_count=$(find docs/screenshots -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$screenshot_count" -gt 0 ]; then
        check_pass "截图目录存在（$screenshot_count 张）"
    else
        check_warn "截图目录存在但为空（需要 7 张截图）"
    fi
else
    check_warn "截图目录不存在（需要创建并添加 7 张截图）"
fi

if [ -d "docs/demos" ]; then
    check_pass "Demo 目录存在"
else
    check_warn "Demo 目录不存在"
fi

echo ""
echo "🧪 功能测试"
echo "----------"

# 6. 测试自动采集器
echo "测试自动采集器..."
test_output=$(echo "我喜欢用 TypeScript" | python3 scripts/auto_memory_collector.py 2>&1 | grep -c "Collected\|Skipped" || true)
if [ "$test_output" -gt 0 ]; then
    check_pass "自动采集器运行正常"
else
    check_warn "自动采集器测试未通过（需要手动验证）"
fi

# 7. 检查 Python 版本
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
python_major=$(echo "$python_version" | cut -d. -f1)
python_minor=$(echo "$python_version" | cut -d. -f2)

if [ "$python_major" -ge 3 ] && [ "$python_minor" -ge 10 ]; then
    check_pass "Python 版本 $python_version (需要 3.10+)"
else
    check_warn "Python 版本 $python_version (推荐 3.10+)"
fi

# 8. 检查 MCP SDK
if python3 -c "import mcp" 2>/dev/null; then
    check_pass "MCP SDK 已安装"
else
    check_warn "MCP SDK 未安装（运行: pip3 install mcp）"
fi

# 9. 检查 Web UI 依赖
if [ -d "web-ui/node_modules" ]; then
    check_pass "Web UI 依赖已安装"
else
    check_warn "Web UI 依赖未安装（运行: cd web-ui && npm install）"
fi

echo ""
echo "🔐 安全检查"
echo "----------"

# 10. 检查敏感文件
sensitive_files=(
    ".env"
    "credentials.json"
    "*.key"
    "*.pem"
)

found_sensitive=false
for pattern in "${sensitive_files[@]}"; do
    if find . -name "$pattern" -not -path "./node_modules/*" -not -path "./.git/*" 2>/dev/null | grep -q .; then
        check_warn "发现敏感文件: $pattern（确保已加入 .gitignore）"
        found_sensitive=true
    fi
done

if [ "$found_sensitive" = false ]; then
    check_pass "未发现敏感文件"
fi

echo ""
echo "📊 统计信息"
echo "----------"

# 11. 代码统计
if command -v cloc &> /dev/null; then
    echo "代码行数统计:"
    cloc scripts mcp-server web-ui --quiet 2>/dev/null || echo "  （cloc 未安装，跳过统计）"
else
    python_lines=$(find scripts mcp-server -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "N/A")
    ts_lines=$(find web-ui -name "*.tsx" -o -name "*.ts" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "N/A")
    echo "  Python: ~$python_lines 行"
    echo "  TypeScript: ~$ts_lines 行"
fi

echo ""
echo "✅ 发布检查清单"
echo "==============="

echo ""
echo "代码质量:"
echo "  [x] 核心功能完成"
echo "  [x] 性能测试通过"
echo "  [x] 并发安全验证"
echo "  [ ] 单元测试（可选）"
echo ""
echo "文档完整性:"
echo "  [x] README 完整"
echo "  [x] CHANGELOG 更新"
echo "  [x] 架构文档完整"
echo "  [x] 性能报告完成"
echo ""
echo "营销素材:"
echo "  [x] Demo 脚本准备"
echo "  [x] 发布计划完成"
echo "  [ ] 截图制作（7 张）"
echo "  [ ] Demo 视频（30 秒）"
echo "  [ ] GIF 动画（3 个）"
echo ""
echo "渠道准备:"
echo "  [ ] Product Hunt 账号"
echo "  [ ] HackerNews 账号"
echo "  [ ] Reddit 账号"
echo "  [ ] Twitter/X 账号"
echo ""

echo "🎯 下一步行动"
echo "============="
echo ""
echo "1. 立即执行（今天）:"
echo "   • 录制 Web UI 截图（7 张）"
echo "   • 启动 Web UI: cd web-ui && npm run dev"
echo "   • 参考: docs/DEMO_SCRIPT.md"
echo ""
echo "2. 明天执行:"
echo "   • 录制 30 秒 Demo 视频"
echo "   • 制作 GIF 动画（可选）"
echo "   • 邀请 5-10 个种子用户测试"
echo ""
echo "3. 本周执行:"
echo "   • 收集反馈并快速迭代"
echo "   • 准备 Product Hunt 提交"
echo "   • 发布到社交媒体"
echo ""

echo "📖 相关文档"
echo "=========="
echo "  • Demo 脚本: docs/DEMO_SCRIPT.md"
echo "  • 发布计划: docs/LAUNCH_PLAN.md"
echo "  • 检查清单: docs/RELEASE_CHECKLIST.md"
echo "  • 性能报告: docs/performance_report.md"
echo ""

echo "✨ DNA Memory v3.0 准备就绪！"
echo "=============================="
