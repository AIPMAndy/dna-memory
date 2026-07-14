#!/usr/bin/env python3
"""
DNA Memory 统一命令行入口
"""

import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent / "scripts"

COMMANDS = {
    'manage': {
        'script': 'memory_manager.py',
        'description': '记忆管理（查看、搜索、编辑、删除）',
        'examples': [
            'dna manage list --limit 10',
            'dna manage search webbridge',
            'dna manage view 9',
            'dna manage update 9 --weight 1.0',
            'dna manage delete 9 --confirm',
            'dna manage stats',
        ]
    },
    'reflect': {
        'script': 'lightweight_reflection.py',
        'description': '记忆升华（轻量级，不调用LLM）',
        'examples': [
            'dna reflect status',
            'dna reflect run',
            'dna reflect run --force',
            'dna reflect config',
        ]
    },
    'monitor': {
        'script': 'lightweight_monitor.py',
        'description': '性能监控',
        'examples': [
            'dna monitor check',
            'dna monitor auto-clean',
        ]
    },
    'ask': {
        'script': 'dna_agent.py',
        'description': '智能问答（自动注入相关记忆）',
        'examples': [
            'dna ask "浏览器操作用什么工具？"',
            'dna ask "如何优化性能？" --agent hermes',
        ]
    },
    'sync': {
        'script': 'sync_to_claude.py',
        'description': '同步高优先级记忆到 Claude Code Memory',
        'examples': [
            'dna sync',
        ]
    },
    'memory': {
        'script': 'memory_cli.py',
        'description': '统一长期记忆索引（状态、重建、维护）',
        'examples': [
            'dna memory status --json',
            'dna memory reindex --json',
            'dna memory maintain daily --json',
            'dna memory maintain weekly --json',
            'dna memory maintain monthly --json',
        ]
    },
    'skills': {
        'script': 'skills_cli.py',
        'description': '跨客户端 Skill 管理（清单、诊断、同步）',
        'examples': [
            'dna skills inventory --json',
            'dna skills sync --json',
        ]
    },
}


def print_help():
    print("DNA Memory - 智能记忆管理系统")
    print("=" * 70)
    print("\n可用命令:\n")

    for cmd, info in COMMANDS.items():
        print(f"  {cmd:12s} - {info['description']}")

    print("\n使用示例:\n")
    for cmd, info in COMMANDS.items():
        print(f"  # {info['description']}")
        for example in info['examples'][:2]:
            print(f"  {example}")
        print()

    print("详细帮助:")
    print("  dna <command> --help")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command = sys.argv[1]

    if command in ['help', '-h', '--help']:
        print_help()
        sys.exit(0)

    if command not in COMMANDS:
        print(f"❌ 未知命令: {command}")
        print(f"\n可用命令: {', '.join(COMMANDS.keys())}")
        print(f"使用 'dna help' 查看帮助")
        sys.exit(1)

    # 执行对应的脚本
    script_path = SCRIPT_DIR / COMMANDS[command]['script']

    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        sys.exit(1)

    # 传递剩余参数
    args = sys.argv[2:]

    try:
        result = subprocess.run(
            ['python3', '-m', 'scripts.' + script_path.stem] + args,
            check=False,
            cwd=str(Path(__file__).parent),
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n中断执行")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
