#!/usr/bin/env python3
"""
DNA Memory - 高级统计模块
提供更详细的记忆分析统计
"""

import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time


def get_detailed_stats():
    """获取详细统计信息"""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # 基础统计
    cursor.execute("SELECT COUNT(*) FROM memory")
    stats["total"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE short_term = 1")
    stats["short_term"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE long_term = 1")
    stats["long_term"] = cursor.fetchone()[0]
    
    # 类型分布
    cursor.execute("SELECT type, COUNT(*) FROM memory GROUP BY type")
    stats["type_dist"] = dict(cursor.fetchall())
    
    # 权重分布
    cursor.execute("SELECT AVG(weight), MIN(weight), MAX(weight) FROM memory")
    avg, min_w, max_w = cursor.fetchone()
    stats["weight_avg"] = round(avg, 3) if avg else 0
    stats["weight_min"] = round(min_w, 3) if min_w else 0
    stats["weight_max"] = round(max_w, 3) if max_w else 0
    
    # 高权重记忆（重要）
    cursor.execute("SELECT COUNT(*) FROM memory WHERE weight >= 0.8")
    stats["high_weight"] = cursor.fetchone()[0]
    
    # 低权重记忆（可能需要遗忘）
    cursor.execute("SELECT COUNT(*) FROM memory WHERE weight < 0.3")
    stats["low_weight"] = cursor.fetchone()[0]
    
    # 标签分析
    cursor.execute("SELECT tags FROM memory WHERE tags IS NOT NULL AND tags != ''")
    all_tags = []
    for row in cursor.fetchall():
        if row[0]:
            all_tags.extend([t.strip() for t in row[0].split(",")])
    
    tag_counts = Counter(all_tags)
    stats["top_tags"] = dict(tag_counts.most_common(10))
    
    # 最近活动
    cursor.execute("SELECT COUNT(*) FROM memory WHERE updated > ?", (time.time() - 86400,))
    stats["updated_24h"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE created > ?", (time.time() - 86400,))
    stats["created_24h"] = cursor.fetchone()[0]
    
    # 关联统计
    cursor.execute("SELECT COUNT(*) FROM memory_relations")
    stats["relations"] = cursor.fetchone()[0]
    
    conn.close()
    return stats


def print_stats():
    """打印统计报告"""
    stats = get_detailed_stats()
    
    print("=" * 40)
    print("🧬 DNA Memory 统计报告")
    print("=" * 40)
    
    print(f"\n📊 总量统计:")
    print(f"   总记忆: {stats['total']} 条")
    print(f"   短期记忆: {stats['short_term']} 条")
    print(f"   长期记忆: {stats['long_term']} 条")
    print(f"   记忆关联: {stats['relations']} 条")
    
    print(f"\n⚖️ 权重分布:")
    print(f"   平均权重: {stats['weight_avg']}")
    print(f"   权重范围: {stats['weight_min']} ~ {stats['weight_max']}")
    print(f"   高权重(≥0.8): {stats['high_weight']} 条")
    print(f"   低权重(<0.3): {stats['low_weight']} 条 ⚠️")
    
    print(f"\n🏷️ 类型分布:")
    for t, c in stats["type_dist"].items():
        print(f"   {t}: {c} 条")
    
    print(f"\n🏷️ 热门标签:")
    for tag, count in stats["top_tags"].items():
        print(f"   #{tag}: {count}")
    
    print(f"\n📈 活跃度 (24h):")
    print(f"   新增: {stats['created_24h']} 条")
    print(f"   更新: {stats['updated_24h']} 条")
    
    print("\n" + "=" * 40)
    
    # 建议
    if stats["low_weight"] > 20:
        print("💡 建议: 运行 `evolve.py forget` 清理低权重记忆")
    if stats["created_24h"] == 0:
        print("💡 建议: 今天还没有新记忆，可以聊聊天积累素材")
    
    return stats


if __name__ == "__main__":
    print_stats()
