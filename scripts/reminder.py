#!/usr/bin/env python3
"""
DNA Memory - 智能提醒模块
基于记忆主动提醒用户
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time


# 提醒规则
REMINDERS = [
    {
        "name": "重要偏好",
        "condition": lambda stats: stats.get("high_weight", 0) > 0,
        "query": "preference",
        "template": "你之前说过：{content}"
    },
    {
        "name": "待完成事项",
        "condition": lambda stats: stats.get("todos", 0) > 0,
        "query": "todo",
        "template": "还有待办：{content}"
    },
    {
        "name": "技能回顾",
        "condition": lambda stats: stats.get("skills", 0) > 3,
        "query": "skill",
        "template": "你擅长的技能：{content}"
    }
]


def get_memory_stats():
    """获取记忆统计"""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE weight >= 0.8")
    stats["high_weight"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE type = 'skill'")
    stats["skills"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE content LIKE '%TODO%' OR content LIKE '%待办%'")
    stats["todos"] = cursor.fetchone()[0]
    
    conn.close()
    return stats


def get_random_memory(mem_type=None, min_weight=0.5):
    """获取随机记忆"""
    conn = get_db()
    cursor = conn.cursor()
    
    if mem_type:
        cursor.execute("""
            SELECT content, type FROM memory 
            WHERE type = ? AND weight >= ?
            ORDER BY RANDOM() LIMIT 1
        """, (mem_type, min_weight))
    else:
        cursor.execute("""
            SELECT content, type FROM memory 
            WHERE weight >= ?
            ORDER BY RANDOM() LIMIT 1
        """, (min_weight,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"content": row[0], "type": row[1]}
    return None


def generate_reminders():
    """生成提醒"""
    stats = get_memory_stats()
    reminders = []
    
    for rule in REMINDERS:
        if rule["condition"](stats):
            # 获取相关记忆
            mem = get_random_memory(rule["query"])
            if mem:
                reminders.append({
                    "name": rule["name"],
                    "message": rule["template"].format(content=mem["content"]),
                    "type": mem["type"]
                })
    
    return reminders


def check_and_remind():
    """检查并提醒"""
    reminders = generate_reminders()
    
    if not reminders:
        print("✅ 无需提醒")
        return []
    
    print(f"🔔 生成 {len(reminders)} 条提醒:")
    for r in reminders:
        print(f"   [{r['name']}] {r['message']}")
    
    return reminders


if __name__ == "__main__":
    check_and_remind()
