#!/usr/bin/env python3
"""
DNA Memory - 自动采集模块
从 OpenClaw 对话历史中自动提取记忆
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from memory_db import get_db
import time


# 需要提取的关键模式
PATTERNS = {
    "preference": [
        (r"我喜欢(.+)", "preference"),
        (r"我喜欢(.+)", "preference"),
        (r"我不喜欢(.+)", "preference"),
        (r"不要(.+)", "preference"),
        (r"不要(.+)", "preference"),
        (r"prefer (.+)", "preference"),
        (r"don't like (.+)", "preference"),
    ],
    "skill": [
        (r"会(.+)编程", "skill"),
        (r"会用(.+)", "skill"),
        (r"擅长(.+)", "skill"),
        (r"can use (.+)", "skill"),
    ],
    "fact": [
        (r"我是(.+)", "fact"),
        (r"我在(.+)", "fact"),
        (r"做(.+)工作", "fact"),
        (r"在(.+)工作", "fact"),
    ]
}


def extract_from_text(text):
    """从文本中提取记忆"""
    memories = []
    
    for pattern, mem_type in PATTERNS["preference"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            content = match.strip()
            if len(content) > 2 and len(content) < 100:
                memories.append({
                    "content": content,
                    "type": "preference",
                    "confidence": 0.7
                })
    
    return memories


def scan_conversation_history(days=7, limit=100):
    """扫描对话历史提取记忆"""
    # 查找 OpenClaw 对话文件
    memory_dir = Path.home() / ".openclaw" / "memory"
    
    if not memory_dir.exists():
        print("⚠️ 未找到 OpenClaw memory 目录")
        return []
    
    all_memories = []
    
    # 扫描 memory 文件
    for md in memory_dir.glob("*.md"):
        # 检查修改时间
        mtime = datetime.fromtimestamp(md.stat().st_mtime)
        if datetime.now() - mtime > timedelta(days=days):
            continue
        
        try:
            content = md.read_text()
            memories = extract_from_text(content)
            all_memories.extend(memories)
        except:
            pass
    
    # 去重
    seen = set()
    unique_memories = []
    for m in all_memories:
        key = m["content"]
        if key not in seen:
            seen.add(key)
            unique_memories.append(m)
    
    return unique_memories


def auto_collect(days=7, save=True, min_confidence=0.6):
    """自动采集记忆"""
    print(f"🔍 扫描最近 {days} 天的对话历史...")
    
    memories = scan_conversation_history(days=days)
    print(f"   发现 {len(memories)} 条潜在记忆")
    
    if not save:
        return memories
    
    # 保存到数据库
    conn = get_db()
    cursor = conn.cursor()
    
    saved = 0
    for mem in memories:
        if mem["confidence"] < min_confidence:
            continue
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM memory WHERE content = ?", (mem["content"],))
        if cursor.fetchone():
            continue
        
        cursor.execute("""
            INSERT INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
            VALUES (?, ?, 'auto,extracted', ?, 1, 0, ?, ?)
        """, (
            mem["content"],
            mem["type"],
            mem["confidence"],
            time.time(),
            time.time()
        ))
        saved += 1
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ 保存了 {saved} 条新记忆")
    return memories


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="扫描天数")
    parser.add_argument("--no-save", action="store_true", help="只显示不保存")
    parser.add_argument("--confidence", type=float, default=0.6, help="最低置信度")
    args = parser.parse_args()
    
    result = auto_collect(
        days=args.days, 
        save=not args.no_save,
        min_confidence=args.confidence
    )
    print(f"\n💡 完成! 共 {len(result)} 条")
