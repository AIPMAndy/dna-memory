#!/usr/bin/env python3
"""
DNA Memory - CLI 交互界面
提供交互式命令行工具
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
from scripts.evolve import add_working_memory, get_working_memory
from scripts.semantic_search import semantic_search
import time


def cmd_remember(args):
    """记录记忆"""
    content = " ".join(args)
    if not content:
        print("❌ 请输入记忆内容")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
        VALUES (?, 'fact', 'cli', 0.6, 1, 0, ?, ?)
    """, (content, time.time(), time.time()))
    conn.commit()
    conn.close()
    print(f"✅ 已记录: {content}")


def cmd_recall(query):
    """搜索记忆"""
    if not query:
        print("❌ 请输入搜索关键词")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT content, type, weight FROM memory WHERE content LIKE ?", (f"%{query}%",))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        # 语义搜索
        semantic = semantic_search(query, top_k=5)
        if semantic:
            print(f"🔍 语义搜索 '{query}':")
            for s in semantic:
                print(f"   [{s['similarity']:.2f}] {s['content']}")
        else:
            print(f"❌ 没有找到: {query}")
    else:
        print(f"🔍 找到 {len(results)} 条:")
        for r in results:
            print(f"   [{r[2]:.2f}] {r[0]}")


def cmd_stats():
    """显示统计"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM memory")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE short_term = 1")
    short = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE long_term = 1")
    long_term = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(weight) FROM memory")
    avg = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print("=" * 30)
    print("🧬 DNA Memory 统计")
    print("=" * 30)
    print(f"   总记忆: {total}")
    print(f"   短期: {short}")
    print(f"   长期: {long_term}")
    print(f"   平均权重: {avg:.2f}")
    print("=" * 30)


def cmd_working(args):
    """工作记忆操作"""
    if not args:
        # 显示
        mem = get_working_memory()
        print(f"📌 工作记忆 ({len(mem)}/7):")
        for i, m in enumerate(mem, 1):
            print(f"   {i}. {m['content']}")
    else:
        content = " ".join(args)
        add_working_memory(content, 0.9)
        print(f"✅ 已添加: {content}")


def main():
    if len(sys.argv) < 2:
        print("""
🧬 DNA Memory CLI

用法:
  dna remember <内容>    记录新记忆
  dna recall <关键词>   搜索记忆
  dna stats            显示统计
  dna working          显示工作记忆
  dna working <内容>   添加到工作记忆
        """)
        sys.exit(1)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == "remember":
        cmd_remember(args)
    elif cmd == "recall":
        cmd_recall(args[0] if args else "")
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "working":
        cmd_working(args)
    else:
        print(f"❌ 未知命令: {cmd}")


if __name__ == "__main__":
    main()
