#!/bin/bash
# DNA Memory 快速修复脚本
# 自动修复常见问题

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

echo "🔧 DNA Memory 快速修复工具"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计
TOTAL_FIXES=0
TOTAL_FILES=0

# 1. 修复硬编码路径 (.openclaw → .claude)
fix_hardcoded_paths() {
    echo "📝 修复硬编码路径..."

    local files=(
        "scripts/knowme_link.py"
        "scripts/session_memory.py"
        "scripts/memory_extractor.py"
        "scripts/backup.py"
        "scripts/thought_memory.py"
        "scripts/enhanced_recall.py"
        "scripts/dna_memory_daemon.py"
        "scripts/reflect_pending.py"
        "scripts/autocollect.py"
    )

    for file in "${files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            # 先备份
            cp "$PROJECT_ROOT/$file" "$PROJECT_ROOT/$file.bak"

            # 替换 .openclaw → .claude
            if grep -q "\.openclaw" "$PROJECT_ROOT/$file"; then
                sed -i.tmp 's/\.openclaw/.claude/g' "$PROJECT_ROOT/$file"
                rm "$PROJECT_ROOT/$file.tmp" 2>/dev/null || true
                echo -e "  ${GREEN}✓${NC} $file"
                TOTAL_FIXES=$((TOTAL_FIXES + 1))
            fi
        fi
    done

    echo ""
}

# 2. 清理 Python 缓存
clean_cache() {
    echo "🧹 清理 Python 缓存..."

    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true

    echo -e "  ${GREEN}✓${NC} 缓存已清理"
    echo ""
}

# 3. 验证 Python 语法
validate_syntax() {
    echo "🔍 验证 Python 语法..."

    local errors=0
    for file in "$SCRIPTS_DIR"/*.py; do
        if [ -f "$file" ]; then
            if ! python3 -m py_compile "$file" 2>/dev/null; then
                echo -e "  ${RED}✗${NC} $(basename "$file") - 语法错误"
                errors=$((errors + 1))
            fi
            TOTAL_FILES=$((TOTAL_FILES + 1))
        fi
    done

    if [ $errors -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} 所有文件语法正确 ($TOTAL_FILES 个)"
    else
        echo -e "  ${RED}✗${NC} 发现 $errors 个文件有语法错误"
    fi

    echo ""
    return $errors
}

# 4. 运行代码质量检查
run_quality_check() {
    echo "📊 运行代码质量检查..."

    if [ -f "$PROJECT_ROOT/quick_fix.py" ]; then
        python3 "$PROJECT_ROOT/quick_fix.py" --check || true
    else
        echo -e "  ${YELLOW}⚠${NC}  quick_fix.py 不存在，跳过"
    fi

    echo ""
}

# 5. 恢复备份文件
restore_backups() {
    echo "↩️  恢复备份文件..."

    for backup in "$PROJECT_ROOT"/scripts/*.bak; do
        if [ -f "$backup" ]; then
            original="${backup%.bak}"
            mv "$backup" "$original"
            echo -e "  ${GREEN}✓${NC} 已恢复 $(basename "$original")"
        fi
    done

    echo ""
}

# 6. 删除备份文件
remove_backups() {
    echo "🗑️  删除备份文件..."

    find "$PROJECT_ROOT/scripts" -type f -name "*.bak" -delete 2>/dev/null || true

    echo -e "  ${GREEN}✓${NC} 备份文件已删除"
    echo ""
}

# 主菜单
show_menu() {
    echo ""
    echo "请选择操作:"
    echo "  1) 修复硬编码路径 (.openclaw → .claude)"
    echo "  2) 清理 Python 缓存"
    echo "  3) 验证 Python 语法"
    echo "  4) 运行代码质量检查"
    echo "  5) 执行所有修复 (1+2+3+4)"
    echo "  6) 恢复备份文件"
    echo "  7) 删除备份文件"
    echo "  0) 退出"
    echo ""
    read -p "选择 [0-7]: " choice
    echo ""
}

# 主逻辑
main() {
    if [ "$1" == "--auto" ]; then
        # 自动模式：执行所有修复
        fix_hardcoded_paths
        clean_cache
        validate_syntax
        run_quality_check

        echo "================================"
        echo -e "${GREEN}✓ 自动修复完成${NC}"
        echo "  修复文件数: $TOTAL_FIXES"
        echo "  检查文件数: $TOTAL_FILES"
        echo ""
        echo "提示："
        echo "  - 原始文件已备份为 .bak"
        echo "  - 运行 './quick_fix.sh --restore' 可恢复"
        echo "  - 运行 './quick_fix.sh --clean' 可删除备份"
        echo ""
        exit 0
    fi

    if [ "$1" == "--restore" ]; then
        restore_backups
        exit 0
    fi

    if [ "$1" == "--clean" ]; then
        remove_backups
        exit 0
    fi

    # 交互模式
    while true; do
        show_menu

        case $choice in
            1)
                fix_hardcoded_paths
                ;;
            2)
                clean_cache
                ;;
            3)
                validate_syntax
                ;;
            4)
                run_quality_check
                ;;
            5)
                fix_hardcoded_paths
                clean_cache
                validate_syntax
                run_quality_check
                echo "================================"
                echo -e "${GREEN}✓ 所有修复完成${NC}"
                echo ""
                ;;
            6)
                restore_backups
                ;;
            7)
                remove_backups
                ;;
            0)
                echo "退出"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选择${NC}"
                ;;
        esac

        read -p "按回车继续..."
    done
}

# 显示帮助
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "用法: ./quick_fix.sh [选项]"
    echo ""
    echo "选项:"
    echo "  --auto      自动执行所有修复"
    echo "  --restore   恢复备份文件"
    echo "  --clean     删除备份文件"
    echo "  --help      显示此帮助"
    echo ""
    echo "交互模式:"
    echo "  ./quick_fix.sh  (无参数进入交互菜单)"
    echo ""
    exit 0
fi

# 运行
main "$@"
