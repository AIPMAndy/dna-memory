#!/usr/bin/env python3
"""
DNA Memory 快速优化脚本
自动修复常见问题，提升代码质量

用法:
    python3 quick_fix.py --check    # 检查问题
    python3 quick_fix.py --fix      # 自动修复
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

class Issue:
    def __init__(self, file_path: Path, line_no: int, issue_type: str, description: str):
        self.file_path = file_path
        self.line_no = line_no
        self.issue_type = issue_type
        self.description = description

    def __str__(self):
        return f"[{self.issue_type}] {self.file_path}:{self.line_no} - {self.description}"

def check_bare_except(file_path: Path) -> List[Issue]:
    """检查裸 except 语句"""
    issues = []
    content = file_path.read_text()
    for i, line in enumerate(content.splitlines(), 1):
        if re.match(r'^\s*except\s*:\s*$', line):
            issues.append(Issue(
                file_path, i, "BARE_EXCEPT",
                "裸 except 语句，建议指定异常类型或添加日志"
            ))
        elif re.match(r'^\s*except\s+Exception\s*:\s*$', line):
            # 检查下一行是否是 pass
            lines = content.splitlines()
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line == "pass":
                    issues.append(Issue(
                        file_path, i, "SILENT_EXCEPTION",
                        "静默吞掉异常，建议至少在 debug 模式输出日志"
                    ))
    return issues

def check_hardcoded_paths(file_path: Path) -> List[Issue]:
    """检查硬编码路径"""
    issues = []
    content = file_path.read_text()
    for i, line in enumerate(content.splitlines(), 1):
        if '.openclaw' in line and 'openclaw' not in str(file_path):
            issues.append(Issue(
                file_path, i, "HARDCODED_PATH",
                "使用了 .openclaw 路径，建议改为 .claude 或使用配置"
            ))
    return issues

def check_missing_docstrings(file_path: Path) -> List[Issue]:
    """检查缺失的 docstring"""
    issues = []
    content = file_path.read_text()
    lines = content.splitlines()

    for i, line in enumerate(lines):
        # 检测函数定义
        if re.match(r'^\s*def\s+\w+\s*\(', line):
            # 检查是否有 docstring
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not (next_line.startswith('"""') or next_line.startswith("'''")):
                    # 跳过简单的私有函数
                    func_name = re.search(r'def\s+(\w+)', line).group(1)
                    if not func_name.startswith('_'):
                        issues.append(Issue(
                            file_path, i + 1, "MISSING_DOCSTRING",
                            f"公开函数 {func_name} 缺少 docstring"
                        ))
    return issues

def check_todos(file_path: Path) -> List[Issue]:
    """检查 TODO 注释"""
    issues = []
    content = file_path.read_text()
    for i, line in enumerate(content.splitlines(), 1):
        if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
            issues.append(Issue(
                file_path, i, "TODO",
                line.strip()
            ))
    return issues

def analyze_project() -> Tuple[List[Issue], dict]:
    """分析整个项目"""
    all_issues = []
    stats = {
        "total_files": 0,
        "total_issues": 0,
        "by_type": {}
    }

    print("🔍 开始扫描项目...")

    for py_file in SCRIPTS_DIR.glob("*.py"):
        stats["total_files"] += 1
        print(f"  扫描: {py_file.name}")

        issues = []
        issues.extend(check_bare_except(py_file))
        issues.extend(check_hardcoded_paths(py_file))
        issues.extend(check_missing_docstrings(py_file))
        issues.extend(check_todos(py_file))

        all_issues.extend(issues)

        for issue in issues:
            stats["by_type"][issue.issue_type] = stats["by_type"].get(issue.issue_type, 0) + 1

    stats["total_issues"] = len(all_issues)
    return all_issues, stats

def print_report(issues: List[Issue], stats: dict):
    """打印报告"""
    print("\n" + "="*80)
    print("📊 DNA Memory 代码质量报告")
    print("="*80)

    print(f"\n📁 扫描文件数: {stats['total_files']}")
    print(f"⚠️  发现问题数: {stats['total_issues']}")

    if stats["by_type"]:
        print(f"\n📈 问题分布:")
        for issue_type, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
            print(f"  - {issue_type}: {count}")

    if issues:
        print(f"\n🔍 详细问题列表:\n")

        # 按类型分组
        by_type = {}
        for issue in issues:
            if issue.issue_type not in by_type:
                by_type[issue.issue_type] = []
            by_type[issue.issue_type].append(issue)

        for issue_type, type_issues in by_type.items():
            print(f"\n[{issue_type}] ({len(type_issues)} 个)")
            for issue in type_issues[:10]:  # 只显示前 10 个
                print(f"  {issue}")
            if len(type_issues) > 10:
                print(f"  ... 还有 {len(type_issues) - 10} 个")

    print("\n" + "="*80)
    print("💡 建议:")
    print("  1. 运行 'python3 quick_fix.py --fix' 自动修复部分问题")
    print("  2. 手动处理 BARE_EXCEPT 和 SILENT_EXCEPTION")
    print("  3. 为公开函数添加 docstring")
    print("="*80 + "\n")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 quick_fix.py [--check|--fix]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "--check":
        issues, stats = analyze_project()
        print_report(issues, stats)

        if stats["total_issues"] > 0:
            sys.exit(1)
        else:
            print("✅ 没有发现问题！")

    elif mode == "--fix":
        print("🔧 自动修复功能开发中...")
        print("   当前版本只支持 --check 模式")
        print("   请根据报告手动修复问题")

    else:
        print(f"未知选项: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
