#!/usr/bin/env python3
"""
DNA Memory - 记忆分析模块
深度分析用户行为模式
"""

import json
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time


def analyze_time_patterns():
    """分析时间模式"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT created, type FROM memory 
        WHERE created > ?
    """, (time.time() - 86400 * 30,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 按小时分布
    hours = [datetime.fromtimestamp(row[0]).hour for row in rows]
    hour_counts = Counter(hours)
    
    # 按星期分布
    weekdays = [datetime.fromtimestamp(row[0]).weekday() for row in rows]
    weekday_counts = Counter(weekdays)
    
    return {
        "hours": dict(hour_counts),
        "weekdays": {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"},
        "weekday_counts": dict(weekday_counts),
        "peak_hour": hour_counts.most_common(1)[0] if hour_counts else None
    }


def analyze_content_patterns():
    """分析内容模式"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有记忆内容
    cursor.execute("SELECT content, type, tags FROM memory WHERE long_term = 1")
    rows = cursor.fetchall()
    
    # 提取关键词
    keywords = []
    for content, _, tags in rows:
        if tags:
            keywords.extend([t.strip() for t in tags.split(",")])
    
    keyword_counts = Counter(keywords)
    
    # 类型分布
    type_counts = {}
    for content, mem_type, _ in rows:
        type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
    
    return {
        "top_keywords": keyword_counts.most_common(10),
        "type_distribution": type_counts
    }


def analyze_weight_distribution():
    """分析权重分布"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT weight FROM memory")
    weights = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not weights:
        return {}
    
    # 分组统计
    ranges = {
        "0-0.3": 0,
        "0.3-0.5": 0,
        "0.5-0.7": 0,
        "0.7-0.9": 0,
        "0.9-1.0": 0
    }
    
    for w in weights:
        if w < 0.3:
            ranges["0-0.3"] += 1
        elif w < 0.5:
            ranges["0.3-0.5"] += 1
        elif w < 0.7:
            ranges["0.5-0.7"] += 1
        elif w < 0.9:
            ranges["0.7-0.9"] += 1
        else:
            ranges["0.9-1.0"] += 1
    
    return ranges


def generate_insights():
    """生成洞察"""
    insights = []
    
    # 时间分析
    time_data = analyze_time_patterns()
    if time_data.get("peak_hour"):
        hour, count = time_data["peak_hour"]
        if 22 <= hour or hour <= 6:
            insights.append("🌙 你倾向于在深夜活动")
        elif 6 <= hour <= 9:
            insights.append("🌅 你是一个早起的人")
    
    # 内容分析
    content_data = analyze_content_patterns()
    if content_data.get("top_keywords"):
        top_kw, kw_count = content_data["top_keywords"][0]
        insights.append(f"🏷️ 你最常关注的话题是 #{top_kw} ({kw_count}次)")
    
    if content_data.get("type_distribution"):
        prefs = content_data["type_distribution"].get("preference", 0)
        facts = content_data["type_distribution"].get("fact", 0)
        if prefs > facts * 0.5:
            insights.append("💡 你记录了很多个人偏好")
    
    # 权重分析
    weight_data = analyze_weight_distribution()
    high_weight = weight_data.get("0.9-1.0", 0)
    total = sum(weight_data.values())
    if total > 0 and high_weight / total > 0.3:
        insights.append("⭐ 你有很多重要记忆")
    
    return insights


def full_analysis():
    """完整分析"""
    print("=" * 50)
    print("🧬 DNA Memory 深度分析")
    print("=" * 50)
    
    # 时间模式
    time_data = analyze_time_patterns()
    print("\n⏰ 活跃时间:")
    if time_data.get("peak_hour"):
        hour, count = time_data["peak_hour"]
        print(f"   高峰时段: {hour}:00 (共 {count} 条)")
    
    # 内容模式
    content_data = analyze_content_patterns()
    print("\n📝 内容分析:")
    print(f"   热门标签: {content_data.get('top_keywords', [])[:5]}")
    print(f"   类型分布: {content_data.get('type_distribution', {})}")
    
    # 权重分布
    weight_data = analyze_weight_distribution()
    print("\n⚖️ 权重分布:")
    for range_, count in weight_data.items():
        bar = "█" * count
        print(f"   {range_:10}: {bar} {count}")
    
    # 洞察
    insights = generate_insights()
    print("\n💡 洞察:")
    for insight in insights:
        print(f"   {insight}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--insights", action="store_true", help="只显示洞察")
    args = parser.parse_args()
    
    if args.insights:
        insights = generate_insights()
        for i in insights:
            print(i)
    else:
        full_analysis()
