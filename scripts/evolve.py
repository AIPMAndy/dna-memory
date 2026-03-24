#!/usr/bin/env python3
"""
DNA Memory - 核心模块
让 AI Agent 像人脑一样学习和成长

功能：
- 三层记忆架构（工作/短期/长期）
- 智能遗忘机制（权重衰减 + 自动清理）
- 记忆关联（自动建立关系）
- 语义搜索支持
"""

import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import re

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = MEMORY_DIR / "memory.db"
WORKING_MEMORY_FILE = MEMORY_DIR / "working.json"

# 记忆配置
WORKING_MEMORY_MAX = 7  # 工作记忆容量
FORGET_THRESHOLD = 0.25  # 遗忘阈值
DECAY_FACTOR = 0.95  # 衰减因子
SHORT_TERM_CAPACITY = 100  # 短期记忆容量
AUTO_LINK_SIMILARITY = 0.7  # 自动关联相似度阈值
RECENCY_HALF_LIFE_DAYS = 30.0  # 访问敏感衰减的半衰期（天）

# 记忆类型
TYPES = ["fact", "preference", "skill", "error", "pattern", "insight"]


# ============ 数据库初始化 ============
def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 主记忆表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            type TEXT DEFAULT 'fact',
            tags TEXT DEFAULT '',
            weight REAL DEFAULT 0.5,
            short_term INTEGER DEFAULT 1,
            long_term INTEGER DEFAULT 0,
            created REAL DEFAULT (strftime('%s', 'now')),
            updated REAL DEFAULT (strftime('%s', 'now')),
            last_accessed REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    # Migrate existing databases: add last_accessed if missing
    cursor.execute("PRAGMA table_info(memory)")
    cols = [row[1] for row in cursor.fetchall()]
    if "last_accessed" not in cols:
        # SQLite does not allow non-constant defaults in ALTER TABLE, so add
        # the column without a default and then back-fill immediately.
        cursor.execute(
            "ALTER TABLE memory ADD COLUMN last_accessed REAL"
        )
        # Back-fill: treat existing memories as accessed at their last updated time
        cursor.execute("UPDATE memory SET last_accessed = updated WHERE last_accessed IS NULL")
    
    # 记忆关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id1 INTEGER,
            memory_id2 INTEGER,
            relation_type TEXT DEFAULT 'related',
            weight REAL DEFAULT 0.5,
            created REAL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (memory_id1) REFERENCES memory(id),
            FOREIGN KEY (memory_id2) REFERENCES memory(id)
        )
    """)
    
    # 操作日志
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT,
            details TEXT,
            timestamp REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    
    # FTS5 全文索引（如果不存在则创建）
    try:
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                content, tags, type,
                content_rowid='id',
                tokenize='unicode61'
            )
        """)
    except Exception:
        pass  # FTS5 may not be available on all builds
    
    conn.commit()
    return conn


def get_db():
    """获取数据库连接"""
    return init_db()


# ============ 工作记忆 ============
def load_working_memory():
    """加载工作记忆"""
    if WORKING_MEMORY_FILE.exists():
        try:
            return json.loads(WORKING_MEMORY_FILE.read_text())
        except:
            return []
    return []


def save_working_memory(memories):
    """保存工作记忆"""
    WORKING_MEMORY_FILE.write_text(json.dumps(memories, ensure_ascii=False))


def add_working_memory(content, importance=0.8):
    """添加到工作记忆"""
    memories = load_working_memory()
    
    # 检查是否已存在
    for m in memories:
        if m.get("content") == content:
            m["importance"] = importance
            m["updated"] = time.time()
            break
    else:
        # 添加新记忆
        memories.insert(0, {
            "content": content,
            "importance": importance,
            "created": time.time(),
            "updated": time.time()
        })
    
    # 保持容量限制（按重要性排序）
    memories.sort(key=lambda x: x.get("importance", 0), reverse=True)
    memories = memories[:WORKING_MEMORY_MAX]
    
    save_working_memory(memories)
    log_operation("working_add", content)
    return memories


def get_working_memory():
    """获取工作记忆"""
    return load_working_memory()


def clear_working_memory():
    """清空工作记忆"""
    save_working_memory([])
    log_operation("working_clear", "")
    return []


# ============ 核心记忆操作 ============
def add_memory(content, mem_type="fact", tags="", importance=0.6, short_term=1, long_term=0):
    """添加记忆"""
    conn = get_db()
    cursor = conn.cursor()
    
    now = time.time()
    cursor.execute("""
        INSERT INTO memory (content, type, tags, weight, short_term, long_term, created, updated, last_accessed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (content, mem_type, tags, importance, short_term, long_term, now, now, now))
    
    memory_id = cursor.lastrowid
    
    # 同步更新 FTS5 索引
    try:
        cursor.execute("INSERT INTO memory_fts(rowid, content, tags, type) VALUES (?, ?, ?, ?)",
                       (memory_id, content, tags, mem_type))
    except Exception:
        pass  # FTS table may not exist
    
    conn.commit()
    conn.close()
    
    log_operation("remember", f"{mem_type}: {content[:50]}")
    return memory_id


def search_memories(query, limit=10):
    """搜索记忆 - FTS5 全文搜索 + LIKE 回退，支持多关键词、类型过滤"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 解析类型过滤 (e.g. "type:skill 飞书")
    type_filter = None
    clean_query = query
    type_match = re.match(r'type:(\w+)\s+(.*)', query)
    if type_match:
        type_filter = type_match.group(1)
        clean_query = type_match.group(2)
    
    keywords = [k.strip() for k in clean_query.split() if k.strip()]
    if not keywords:
        conn.close()
        return []
    
    results = []
    
    # 尝试 FTS5 搜索
    try:
        fts_query = " AND ".join(f'"{kw}"' for kw in keywords)
        if type_filter:
            fts_query += f' AND type:{type_filter}'
        
        cursor.execute(f"""
            SELECT m.id, m.content, m.type, m.tags, m.weight, m.short_term, m.long_term,
                   rank
            FROM memory_fts f
            JOIN memory m ON f.rowid = m.id
            WHERE memory_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit))
        
        for row in cursor.fetchall():
            layer = "长期" if row[6] else ("短期" if row[5] else "?")
            results.append({
                "id": row[0], "content": row[1], "type": row[2],
                "tags": row[3], "weight": row[4], "layer": layer
            })
    except Exception:
        pass
    
    # FTS5 没结果或不可用，回退到 LIKE 搜索
    if not results:
        conditions = []
        params = []
        for kw in keywords:
            conditions.append("(content LIKE ? OR tags LIKE ? OR type LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
        
        where = " AND ".join(conditions)
        if type_filter:
            where = f"({where}) AND type = ?"
            params.append(type_filter)
        
        params.append(limit)
        
        cursor.execute(f"""
            SELECT id, content, type, tags, weight, short_term, long_term
            FROM memory 
            WHERE {where}
            ORDER BY weight DESC, updated DESC
            LIMIT ?
        """, params)
        
        for row in cursor.fetchall():
            layer = "长期" if row[6] else ("短期" if row[5] else "?")
            results.append({
                "id": row[0], "content": row[1], "type": row[2],
                "tags": row[3], "weight": row[4], "layer": layer
            })

    # Update last_accessed for retrieved memories (same connection, before close)
    if results:
        ids = [r["id"] for r in results]
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"UPDATE memory SET last_accessed = ? WHERE id IN ({placeholders})",
            [time.time()] + ids,
        )
        conn.commit()

    conn.close()
    return results


def get_memories_by_type(mem_type, limit=50):
    """按类型获取记忆"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, content, tags, weight, created
        FROM memory 
        WHERE type = ?
        ORDER BY weight DESC
        LIMIT ?
    """, (mem_type, limit))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "id": row[0],
            "content": row[1],
            "tags": row[2],
            "weight": row[3],
            "created": row[4]
        })
    
    conn.close()
    return results


# ============ 遗忘机制 ============
def auto_forget(threshold=FORGET_THRESHOLD):
    """自动遗忘低权重记忆"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 删除低权重记忆
    cursor.execute("DELETE FROM memory WHERE weight < ?", (threshold,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    log_operation("forget", f"deleted {deleted} memories")
    return deleted


def auto_decay(factor=DECAY_FACTOR, use_recency: bool = True):
    """权重衰减（可选访问敏感模式）

    当 use_recency=True 时，近期被访问的记忆衰减更慢：
      recency_multiplier = 1 - (1 - factor) * exp(-days_since_access / half_life)
    即访问时间越近（days_since_access → 0），衰减因子越接近 1.0（几乎不衰减）；
    访问时间越久（days_since_access → ∞），衰减因子趋近全局 factor。

    当 use_recency=False 时，退回原先的统一衰减行为。
    """
    import math

    conn = get_db()
    cursor = conn.cursor()

    if not use_recency:
        cursor.execute("UPDATE memory SET weight = weight * ?", (factor,))
        updated = cursor.rowcount
    else:
        now = time.time()
        half_life_seconds = RECENCY_HALF_LIFE_DAYS * 86400.0
        cursor.execute("SELECT id, weight, last_accessed FROM memory")
        rows = cursor.fetchall()
        updated = 0
        for mid, weight, last_accessed in rows:
            if last_accessed is None:
                last_accessed = now
            days_since = max(0.0, (now - last_accessed) / 86400.0)
            # Recency multiplier: recently-accessed memories decay more slowly.
            # At days_since=0  → multiplier=1.0  (no decay, just accessed)
            # At days_since=∞  → multiplier=factor (full base decay, never accessed)
            recency_multiplier = factor + (1.0 - factor) * math.exp(
                -days_since / RECENCY_HALF_LIFE_DAYS
            )
            new_weight = weight * recency_multiplier
            cursor.execute(
                "UPDATE memory SET weight = ? WHERE id = ?", (new_weight, mid)
            )
            updated += 1

    conn.commit()
    conn.close()

    mode = "recency-sensitive" if use_recency else "uniform"
    log_operation("decay", f"decayed {updated} memories ({mode})")
    return updated


# ============ 记忆关联 ============
def auto_link_memories():
    """自动建立记忆关联"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有标签
    cursor.execute("SELECT id, content, tags FROM memory WHERE tags IS NOT NULL AND tags != ''")
    memories = cursor.fetchall()
    
    links_created = 0
    for i, (id1, content1, tags1) in enumerate(memories):
        for id2, content2, tags2 in memories[i+1:]:
            # 检查是否已关联
            cursor.execute("""
                SELECT 1 FROM memory_relations 
                WHERE (memory_id1 = ? AND memory_id2 = ?) OR (memory_id1 = ? AND memory_id2 = ?)
            """, (id1, id2, id2, id1))
            if cursor.fetchone():
                continue
            
            # 相同标签建立关联
            if tags1 and tags2:
                tags_set1 = set(tags1.split(","))
                tags_set2 = set(tags2.split(","))
                common = tags_set1 & tags_set2
                
                if common:
                    cursor.execute("""
                        INSERT INTO memory_relations (memory_id1, memory_id2, relation_type, weight)
                        VALUES (?, ?, 'same_tag', 0.8)
                    """, (id1, id2))
                    links_created += 1
    
    conn.commit()
    conn.close()
    
    log_operation("link", f"created {links_created} links")
    return links_created


def access_memory(memory_id: int):
    """更新指定记忆的 last_accessed 时间戳（供外部调用，例如工作流读取某条记忆后调用）"""
    conn = get_db()
    conn.execute(
        "UPDATE memory SET last_accessed = ? WHERE id = ?", (time.time(), memory_id)
    )
    conn.commit()
    conn.close()
    log_operation("access", f"id={memory_id}")


def get_related_memories(memory_id, limit=5):
    """获取关联记忆"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT m.id, m.content, m.type, m.weight, r.relation_type, r.weight as rel_weight
        FROM memory_relations r
        JOIN memory m ON (m.id = r.memory_id2 OR m.id = r.memory_id1)
        WHERE (r.memory_id1 = ? OR r.memory_id2 = ?) AND m.id != ?
        ORDER BY r.weight DESC
        LIMIT ?
    """, (memory_id, memory_id, memory_id, limit))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "id": row[0],
            "content": row[1],
            "type": row[2],
            "weight": row[3],
            "relation_type": row[4],
            "relation_weight": row[5]
        })
    
    conn.close()
    return results


# ============ 统计 ============
def get_stats():
    """获取统计信息"""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM memory")
    stats["total"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE short_term = 1")
    stats["short_term"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE long_term = 1")
    stats["long_term"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory_relations")
    stats["relations"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(weight) FROM memory")
    stats["avg_weight"] = round(cursor.fetchone()[0] or 0, 3)
    
    # 操作统计
    cursor.execute("""
        SELECT operation, COUNT(*) 
        FROM operations 
        GROUP BY operation
    """)
    stats["operations"] = dict(cursor.fetchall())
    
    conn.close()
    return stats


def log_operation(operation, details):
    """记录操作日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO operations (operation, details) VALUES (?, ?)
    """, (operation, details))
    conn.commit()
    conn.close()


# ============ CLI 命令 ============
def cmd_remember(args):
    """记录记忆"""
    content = " ".join(args.content)
    mem_type = args.type or "fact"
    tags = args.tags or ""
    importance = float(args.importance or 0.6)
    
    add_memory(content, mem_type, tags, importance)
    print(f"✅ 已记录: {content[:50]} [{mem_type}: {importance}]")


def cmd_recall(args):
    """搜索记忆"""
    results = search_memories(args.query, limit=args.limit)
    
    if not results:
        print(f"❌ 没有找到: {args.query}")
        return
    
    print(f"🔍 找到 {len(results)} 条:")
    for r in results:
        layer = r.get('layer', '?')
        print(f"   [{r['weight']:.2f}|{r['type']}|{layer}] {r['content'][:80]}")


def cmd_stats(args):
    """显示统计"""
    stats = get_stats()
    
    print("=" * 40)
    print("🧬 DNA Memory 统计")
    print("=" * 40)
    print(f"   总记忆: {stats['total']}")
    print(f"   短期记忆: {stats['short_term']}")
    print(f"   长期记忆: {stats['long_term']}")
    print(f"   记忆关联: {stats['relations']}")
    print(f"   平均权重: {stats['avg_weight']}")
    print("\n📈 操作统计:")
    for op, count in stats.get("operations", {}).items():
        print(f"   {op}: {count}")
    print("=" * 40)


def cmd_working(args):
    """工作记忆操作"""
    if args.clear:
        clear_working_memory()
        print("🗑️ 已清空工作记忆")
        return
    
    if args.content:
        add_working_memory(args.content, float(args.importance or 0.8))
        print(f"✅ 已添加到工作记忆: {args.content[:50]}")
    else:
        mems = get_working_memory()
        print(f"📌 工作记忆 ({len(mems)}/{WORKING_MEMORY_MAX}):")
        for i, m in enumerate(mems, 1):
            print(f"   {i}. {m['content'][:50]} [⭐{m.get('importance', 0):.1f}]")


def cmd_forget(args):
    """遗忘操作"""
    deleted = auto_forget(float(args.threshold or FORGET_THRESHOLD))
    print(f"🗑️ 已删除 {deleted} 条低权重记忆")


def cmd_decay(args):
    """衰减操作"""
    factor = float(args.factor or DECAY_FACTOR)
    use_recency = not getattr(args, "uniform", False)
    updated = auto_decay(factor, use_recency=use_recency)
    mode = "uniform" if not use_recency else "recency-sensitive"
    print(f"📉 已衰减 {updated} 条记忆权重 (×{factor}, {mode})")


def cmd_link(args):
    """关联操作"""
    links = auto_link_memories()
    print(f"🔗 已创建 {links} 个记忆关联")


# ============ 记忆晋升 & 反思优化 ============
PROMOTE_THRESHOLD = 0.75   # 权重 >= 此值可晋升到长期记忆

def auto_promote(threshold=PROMOTE_THRESHOLD, min_age_days=3):
    """自动将高权重、稳定的短期记忆晋升为长期记忆"""
    import time
    conn = get_db()
    cursor = conn.cursor()
    cutoff = time.time() - (min_age_days * 86400)
    
    cursor.execute("""
        SELECT id, content, type, tags, weight
        FROM memory
        WHERE short_term = 1 AND long_term = 0
          AND weight >= ? AND updated <= ?
    """, (threshold, cutoff))
    
    candidates = cursor.fetchall()
    promoted = 0
    for mid, content, mtype, tags, weight in candidates:
        cursor.execute("""
            UPDATE memory SET long_term = 1, short_term = 0, weight = 1.0
            WHERE id = ?""", (mid,))
        promoted += 1
        print(f"   ⭐ 晋升 [{weight:.2f}] {content[:50]}...")
    
    conn.commit()
    conn.close()
    log_operation("promote", f"promoted {promoted} to long_term")
    return promoted


def find_patterns():
    """从高权重记忆中归纳模式关键词"""
    from collections import Counter
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM memory
        WHERE type IN ('fact','preference','skill') AND weight >= 0.75
        ORDER BY weight DESC LIMIT 20
    """)
    all_words = []
    for (content,) in cursor.fetchall():
        all_words.extend([w.lower() for w in content.split() if len(w) > 3])
    top = [w for w, _ in Counter(all_words).most_common(10)]
    conn.close()
    return top


def cmd_reflect(args):
    """反思：归纳模式 + 晋升到长期记忆"""
    print("🔄 开始反思...")
    keywords = find_patterns()
    print(f"\n📊 关键词模式: {', '.join(keywords[:8])}")
    promoted = auto_promote(
        threshold=float(getattr(args, 'threshold') or PROMOTE_THRESHOLD),
        min_age_days=int(getattr(args, 'min_age') or 3)
    )
    stats = get_stats()
    print(f"\n✅ 晋升完成: {promoted} 条 → 长期记忆")
    print(f"   短期: {stats['short_term']} | 长期: {stats['long_term']}")


def cmd_promote(args):
    """手动晋升指定记忆到长期记忆"""
    conn = get_db()
    cursor = conn.cursor()
    if getattr(args, 'id', None):
        cursor.execute("UPDATE memory SET long_term=1, short_term=0, weight=1.0 WHERE id=?", (args.id,))
        conn.commit()
        print(f"✅ 已晋升 ID={args.id}")
    else:
        cursor.execute("SELECT id, substr(content,1,60), weight, type FROM memory WHERE short_term=1 AND long_term=0 ORDER BY weight DESC LIMIT 20")
        print("📋 可晋升记忆:")
        for row in cursor.fetchall():
            print(f"   #{row[0]} [{row[2]:.2f}] {row[1]}... [{row[3]}]")
        print("\n用法: promote --id <id>")
    conn.close()


def cmd_dedupe(args):
    """去重：合并相似记忆"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, weight FROM memory ORDER BY content")
    all_mem = cursor.fetchall()
    removed = 0
    kept = set()
    for i, (id1, c1, w1) in enumerate(all_mem):
        if id1 in kept: continue
        kept.add(id1)
        for id2, c2, w2 in all_mem[i+1:]:
            if id2 in kept: continue
            if abs(len(c1)-len(c2))<10 and (c1 in c2 or c2 in c1):
                # 保留权重高的
                if w2 > w1:
                    kept.discard(id1); kept.add(id2)
                cursor.execute("DELETE FROM memory WHERE id=?", (id2 if id2 in kept else id1,))
                removed += 1
                print(f"   🗑️ 合并: {c1[:40]}...")
                break
    conn.commit()
    conn.close()
    log_operation("dedupe", f"removed {removed}")
    print(f"✅ 去重完成: 删除 {removed} 条")


# ============ 主函数 ============
def main():
    parser = argparse.ArgumentParser(description="DNA Memory 核心程序")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # remember
    p_remember = subparsers.add_parser("remember", help="记录记忆")
    p_remember.add_argument("content", nargs="+", help="记忆内容")
    p_remember.add_argument("-t", "--type", choices=TYPES, default="fact", help="记忆类型")
    p_remember.add_argument("--tags", default="", help="标签")
    p_remember.add_argument("-i", "--importance", default="0.6", help="重要性 (0-1)")
    
    # recall
    p_recall = subparsers.add_parser("recall", help="搜索记忆")
    p_recall.add_argument("query", help="搜索关键词")
    p_recall.add_argument("-l", "--limit", type=int, default=10, help="返回数量")
    
    # stats
    subparsers.add_parser("stats", help="显示统计")
    
    # working
    p_working = subparsers.add_parser("working", help="工作记忆")
    p_working.add_argument("content", nargs="?", help="记忆内容")
    p_working.add_argument("-i", "--importance", default="0.8", help="重要性")
    p_working.add_argument("--clear", action="store_true", help="清空工作记忆")
    
    # forget
    p_forget = subparsers.add_parser("forget", help="自动遗忘")
    p_forget.add_argument("-t", "--threshold", default=str(FORGET_THRESHOLD), help="遗忘阈值")
    
    # decay
    p_decay = subparsers.add_parser("decay", help="权重衰减（默认访问敏感，近期使用的记忆衰减更慢）")
    p_decay.add_argument("-f", "--factor", default=str(DECAY_FACTOR), help="衰减因子")
    p_decay.add_argument("--uniform", action="store_true", help="退回统一衰减模式（忽略 last_accessed）")
    
    # link
    subparsers.add_parser("link", help="建立记忆关联")
    
    # reflect
    p_reflect = subparsers.add_parser("reflect", help="反思归纳（模式 + 晋升）")
    p_reflect.add_argument("--threshold", default=str(PROMOTE_THRESHOLD), help="晋升权重阈值")
    p_reflect.add_argument("--min-age", default="3", help="最短存活天数")
    
    # promote
    p_promote = subparsers.add_parser("promote", help="手动晋升到长期记忆")
    p_promote.add_argument("--id", type=int, help="记忆ID")
    
    # dedupe
    subparsers.add_parser("dedupe", help="去重合并")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print("\n示例:")
        print("  python3 evolve.py remember 我喜欢简洁的回复 -t preference -i 0.9")
        print("  python3 evolve.py recall 偏好")
        print("  python3 evolve.py stats")
        print("  python3 evolve.py working")
        return
    
    # 执行命令
    if args.command == "remember":
        cmd_remember(args)
    elif args.command == "recall":
        cmd_recall(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "working":
        cmd_working(args)
    elif args.command == "forget":
        cmd_forget(args)
    elif args.command == "decay":
        cmd_decay(args)
    elif args.command == "link":
        cmd_link(args)
    elif args.command == "reflect":
        cmd_reflect(args)
    elif args.command == "promote":
        cmd_promote(args)
    elif args.command == "dedupe":
        cmd_dedupe(args)


if __name__ == "__main__":
    main()
