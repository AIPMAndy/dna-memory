#!/bin/bash
# 快速验证脚本 - 验证 DNA Memory 核心功能

set -e

PROJECT_ROOT="/Users/andy/Desktop/04 AICode/dna-memory-review"
cd "$PROJECT_ROOT"

echo "🧪 DNA Memory 快速验证"
echo "======================"
echo ""

# 1. 初始化数据库
echo "1️⃣ 初始化数据库..."
python3 scripts/evolve.py stats > /dev/null 2>&1
echo "   ✅ 数据库已初始化"
echo ""

# 2. 添加测试记忆
echo "2️⃣ 添加测试记忆..."
python3 scripts/evolve.py remember "这是一条测试记忆：验证系统是否正常工作" -t fact -i 0.8 > /dev/null 2>&1
echo "   ✅ 记忆添加成功"
echo ""

# 3. 搜索记忆
echo "3️⃣ 搜索记忆..."
result=$(python3 scripts/evolve.py recall "测试" 2>&1 | grep -c "测试记忆" || true)
if [ "$result" -gt 0 ]; then
    echo "   ✅ 搜索功能正常"
else
    echo "   ❌ 搜索功能异常"
    exit 1
fi
echo ""

# 4. 测试自动采集器
echo "4️⃣ 测试自动采集器..."
output=$(echo "我喜欢用简洁的代码" | python3 scripts/auto_memory_collector.py 2>&1)
if echo "$output" | grep -q "Collected\|processed"; then
    echo "   ✅ 自动采集器正常"
else
    echo "   ❌ 自动采集器异常"
    exit 1
fi
echo ""

# 5. 检查数据库文件
echo "5️⃣ 检查数据库..."
if [ -f "memory/memory.db" ]; then
    size=$(ls -lh memory/memory.db | awk '{print $5}')
    echo "   ✅ 数据库存在（大小: $size）"
else
    echo "   ❌ 数据库不存在"
    exit 1
fi
echo ""

echo "✅ 所有核心功能验证通过！"
echo ""
echo "📝 下一步："
echo "   • 启动 Web UI: cd web-ui && npm run dev"
echo "   • 查看统计: python3 scripts/evolve.py stats"
echo "   • 阅读文档: cat README.md"
