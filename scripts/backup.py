#!/usr/bin/env python3
"""
DNA Memory - 导出/导入模块
支持 JSON 格式导出备份
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time


def export_all(output_path=None):
    """导出所有记忆"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 导出 memory 表
    cursor.execute("SELECT * FROM memory")
    memories = cursor.fetchall()
    
    # 获取列名
    columns = [desc[0] for desc in cursor.description]
    
    data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "memories": [dict(zip(columns, row)) for row in memories]
    }
    
    # 导出关联
    cursor.execute("SELECT * FROM memory_relations")
    relations = cursor.fetchall()
    if relations:
        rel_columns = [desc[0] for desc in cursor.description]
        data["relations"] = [dict(zip(rel_columns, row)) for row in relations]
    
    conn.close()
    
    if not output_path:
        output_path = Path.home() / ".openclaw" / "memory" / f"dna_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"✅ 导出完成: {output_path}")
    print(f"   记忆: {len(data['memories'])} 条")
    print(f"   关联: {len(data.get('relations', []))} 条")
    
    return data


def import_data(input_path, merge=True):
    """导入记忆"""
    data = json.loads(Path(input_path).read_text())
    
    conn = get_db()
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    
    for mem in data.get("memories", []):
        if merge:
            # 检查是否已存在
            cursor.execute("SELECT id FROM memory WHERE content = ?", (mem.get("content", ""),))
            if cursor.fetchone():
                skipped += 1
                continue
        
        cursor.execute("""
            INSERT INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mem.get("content"),
            mem.get("type", "fact"),
            mem.get("tags", ""),
            mem.get("weight", 0.5),
            mem.get("short_term", 0),
            mem.get("long_term", 0),
            mem.get("created", time.time()),
            time.time()
        ))
        imported += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ 导入完成: {imported} 条新记忆")
    print(f"   跳过: {skipped} 条（已存在）")
    return {"imported": imported, "skipped": skipped}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["export", "import"])
    parser.add_argument("--path", help="文件路径")
    args = parser.parse_args()
    
    if args.command == "export":
        export_all(args.path)
    elif args.command == "import":
        if not args.path:
            print("❌ 请指定 --path")
        else:
            import_data(args.path)
