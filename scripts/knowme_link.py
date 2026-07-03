#!/usr/bin/env python3
"""
DNA Memory - KnowMe 联动模块
自动将 KnowMe 性格分析结果同步到 DNA Memory
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from memory_db import get_db
import time


def sync_from_knowme(knowme_data_path=None):
    """从 KnowMe 同步数据到 DNA Memory"""
    
    # 默认路径
    if not knowme_data_path:
        knowme_data_path = Path.home() / ".openclaw" / "workspace" / "skills" / "knowme" / "output" / "latest.json"
    
    if not Path(knowme_data_path).exists():
        print(f"⚠️ KnowMe 数据文件不存在: {knowme_data_path}")
        # 尝试常见位置
        alt_paths = [
            Path.home() / ".openclaw" / "workspace" / "memory" / "knowme.json",
            Path.home() / ".openclaw" / "memory" / "knowme.json",
        ]
        for p in alt_paths:
            if p.exists():
                knowme_data_path = p
                break
    
    # 读取 KnowMe 数据
    try:
        with open(knowme_data_path) as f:
            data = json.load(f)
    except:
        print("⚠️ 无法读取 KnowMe 数据")
        return {"synced": 0, "errors": ["file not found or invalid"]}
    
    conn = get_db()
    cursor = conn.cursor()
    
    synced = 0
    errors = []
    
    # 同步 MBTI 类型
    if "mbti" in data:
        mbti = data["mbti"]
        content = f"MBTI 类型: {mbti}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
            VALUES (?, 'preference', 'mbti,personality,auto', 0.9, 0, 1, ?, ?)
        """, (content, time.time(), time.time()))
        synced += 1
    
    # 同步核心特质
    if "traits" in data:
        for trait in data["traits"]:
            content = f"核心特质: {trait}"
            cursor.execute("""
                INSERT OR REPLACE INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
                VALUES (?, 'fact', 'trait,personality,auto', 0.7, 0, 1, ?, ?)
            """, (content, time.time(), time.time()))
            synced += 1
    
    # 同步沟通风格
    if "communication_style" in data:
        style = data["communication_style"]
        content = f"沟通风格: {style}"
        cursor.execute("""
            INSERT OR REPLACE INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
            VALUES (?, 'preference', 'communication,personality,auto', 0.8, 0, 1, ?, ?)
        """, (content, time.time(), time.time()))
        synced += 1
    
    # 同步成长建议
    if "growth_advice" in data:
        for advice in data["growth_advice"]:
            content = f"成长建议: {advice}"
            cursor.execute("""
                INSERT OR REPLACE INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
                VALUES (?, 'insight', 'growth,personality,auto', 0.6, 0, 1, ?, ?)
            """, (content, time.time(), time.time()))
            synced += 1
    
    conn.commit()
    conn.close()
    
    return {"synced": synced, "errors": errors}


def export_to_knowme():
    """导出 DNA Memory 数据供 KnowMe 使用"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT content, type, tags, weight 
        FROM memory 
        WHERE long_term = 1 
        ORDER BY weight DESC 
        LIMIT 100
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    data = {
        "preferences": [],
        "facts": [],
        "skills": [],
        "patterns": []
    }
    
    for row in rows:
        content, type_, tags, weight = row
        entry = {"content": content, "weight": weight, "tags": tags}
        
        if type_ == "preference":
            data["preferences"].append(entry)
        elif type_ == "fact":
            data["facts"].append(entry)
        elif type_ == "skill":
            data["skills"].append(entry)
        elif type_ == "pattern":
            data["patterns"].append(entry)
    
    return data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true", help="从 KnowMe 同步")
    parser.add_argument("--export", action="store_true", help="导出到 KnowMe")
    parser.add_argument("--path", help="KnowMe 数据路径")
    args = parser.parse_args()
    
    if args.sync:
        result = sync_from_knowme(args.path)
        print(f"✅ 同步完成: {result['synced']} 条")
    elif args.export:
        data = export_to_knowme()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("请指定 --sync 或 --export")
