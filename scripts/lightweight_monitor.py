#!/usr/bin/env python3
"""
轻量级性能监控 - 确保 DNA Memory 不影响 AI 使用性能
"""

import sqlite3
import time
import sys
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from path_utils import get_db_path

# 性能阈值（严格控制）
PERFORMANCE_LIMITS = {
    'max_total_memories': 500,        # 总记忆上限（降低）
    'max_db_size_mb': 5,              # 数据库大小上限（MB）
    'max_recall_time_ms': 50,         # 查询时间上限（毫秒）
    'max_sync_time_ms': 30,           # 同步时间上限（毫秒）
    'warning_threshold': 0.8,         # 警告阈值（80%）
}


def check_performance() -> dict:
    """检查性能指标"""
    db_path = get_db_path()

    # 1. 检查数据库大小
    db_size_mb = db_path.stat().st_size / (1024 * 1024)

    # 2. 检查记忆数量
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM memory")
    total_memories = cursor.fetchone()[0]

    # 3. 测试查询速度
    start = time.time()
    cursor.execute("SELECT * FROM memory ORDER BY weight DESC LIMIT 10")
    cursor.fetchall()
    recall_time_ms = (time.time() - start) * 1000

    conn.close()

    # 计算健康度
    health_scores = []

    # 记忆数量健康度
    memory_ratio = total_memories / PERFORMANCE_LIMITS['max_total_memories']
    health_scores.append(1 - min(memory_ratio, 1))

    # 数据库大小健康度
    size_ratio = db_size_mb / PERFORMANCE_LIMITS['max_db_size_mb']
    health_scores.append(1 - min(size_ratio, 1))

    # 查询速度健康度
    speed_ratio = recall_time_ms / PERFORMANCE_LIMITS['max_recall_time_ms']
    health_scores.append(1 - min(speed_ratio, 1))

    overall_health = sum(health_scores) / len(health_scores)

    return {
        'db_size_mb': round(db_size_mb, 2),
        'total_memories': total_memories,
        'recall_time_ms': round(recall_time_ms, 2),
        'health_score': round(overall_health, 2),
        'status': 'HEALTHY' if overall_health > 0.7 else 'WARNING' if overall_health > 0.4 else 'CRITICAL',
        'warnings': _generate_warnings(db_size_mb, total_memories, recall_time_ms)
    }


def _generate_warnings(db_size_mb, total_memories, recall_time_ms) -> list:
    """生成警告信息"""
    warnings = []

    if total_memories > PERFORMANCE_LIMITS['max_total_memories'] * PERFORMANCE_LIMITS['warning_threshold']:
        warnings.append(f"记忆数量接近上限 ({total_memories}/{PERFORMANCE_LIMITS['max_total_memories']})")

    if db_size_mb > PERFORMANCE_LIMITS['max_db_size_mb'] * PERFORMANCE_LIMITS['warning_threshold']:
        warnings.append(f"数据库大小接近上限 ({db_size_mb:.1f}/{PERFORMANCE_LIMITS['max_db_size_mb']}MB)")

    if recall_time_ms > PERFORMANCE_LIMITS['max_recall_time_ms']:
        warnings.append(f"查询速度过慢 ({recall_time_ms:.1f}ms)")

    return warnings


def auto_cleanup_if_needed() -> dict:
    """如果性能下降，自动清理"""
    status = check_performance()

    if status['status'] == 'CRITICAL':
        # 执行激进清理
        from performance_optimizer import cleanup_low_weight, archive_old_memories, vacuum_db

        print("⚠️  性能危险，执行自动清理...")

        # 1. 清理低权重记忆（阈值提高到 0.4）
        cleanup_low_weight(threshold=0.4)

        # 2. 归档 60 天未访问的记忆
        archive_old_memories(days=60)

        # 3. 压缩数据库
        vacuum_db()

        # 重新检查
        new_status = check_performance()
        return {
            'cleaned': True,
            'before': status,
            'after': new_status
        }

    return {
        'cleaned': False,
        'status': status
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='DNA Memory 性能监控')
    parser.add_argument('action', choices=['check', 'auto-clean'],
                       default='check', nargs='?',
                       help='操作: check=检查, auto-clean=自动清理')

    args = parser.parse_args()

    if args.action == 'check':
        status = check_performance()

        print("🔍 DNA Memory 性能报告")
        print("=" * 50)
        print(f"数据库大小: {status['db_size_mb']} MB / {PERFORMANCE_LIMITS['max_db_size_mb']} MB")
        print(f"记忆数量: {status['total_memories']} / {PERFORMANCE_LIMITS['max_total_memories']}")
        print(f"查询速度: {status['recall_time_ms']} ms")
        print(f"健康度: {status['health_score']:.0%}")
        print(f"状态: {status['status']}")

        if status['warnings']:
            print(f"\n⚠️  警告:")
            for warning in status['warnings']:
                print(f"  - {warning}")
        else:
            print(f"\n✅ 性能良好")

        if status['status'] == 'CRITICAL':
            print(f"\n💡 建议运行: python3 scripts/lightweight_monitor.py auto-clean")

    elif args.action == 'auto-clean':
        result = auto_cleanup_if_needed()

        if result['cleaned']:
            print("✅ 自动清理完成")
            print(f"健康度: {result['before']['health_score']:.0%} → {result['after']['health_score']:.0%}")
        else:
            print("✅ 性能正常，无需清理")


if __name__ == '__main__':
    main()
