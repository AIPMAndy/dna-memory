#!/usr/bin/env python3
"""
DNA Memory - Webhook 触发器
当满足条件时自动触发动作
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time


# 触发条件配置
TRIGGERS = [
    {
        "name": "新用户偏好",
        "condition": lambda stats: stats.get("created_24h", 0) > 5,
        "action": "reflect",
        "message": "用户今天新增了多条记忆，可能有新的偏好模式"
    },
    {
        "name": "记忆过载",
        "condition": lambda stats: stats.get("total", 0) > 500,
        "action": "compact",
        "message": "记忆数量超过500条，建议整理"
    },
    {
        "name": "低权重过多",
        "condition": lambda stats: stats.get("low_weight", 0) > 30,
        "action": "forget",
        "message": "低权重记忆过多，自动清理"
    }
]


def check_triggers():
    """检查触发条件"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 收集统计
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM memory")
    stats["total"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE weight < 0.3")
    stats["low_weight"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE created > ?", (time.time() - 86400,))
    stats["created_24h"] = cursor.fetchone()[0]
    
    conn.close()
    
    triggered = []
    for t in TRIGGERS:
        if t["condition"](stats):
            triggered.append({
                "name": t["name"],
                "message": t["message"],
                "action": t["action"]
            })
    
    return triggered, stats


def run_trigger(trigger):
    """执行触发动作"""
    action = trigger["action"]
    
    if action == "reflect":
        # 调用 reflect
        from scripts.reflect import reflect
        return reflect(limit=30, save=True)
    
    elif action == "forget":
        from scripts.evolve import auto_forget
        count = auto_forget()
        return {"deleted": count}
    
    elif action == "compact":
        # 暂时留空
        return {"message": "compact not implemented"}
    
    return {}


if __name__ == "__main__":
    triggered, stats = check_triggers()
    
    print("🔍 检查触发器...")
    print(f"   总记忆: {stats.get('total', 0)}")
    print(f"   低权重: {stats.get('low_weight', 0)}")
    print(f"   24h新增: {stats.get('created_24h', 0)}")
    
    if triggered:
        print(f"\n⚡ 触发 {len(triggered)} 个条件:")
        for t in triggered:
            print(f"   - {t['name']}: {t['message']}")
            result = run_trigger(t)
            print(f"     结果: {result}")
    else:
        print("\n✅ 无触发条件")
