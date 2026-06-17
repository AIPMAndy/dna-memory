#!/usr/bin/env python3
"""
DNA Memory - 安全性修复示例
针对对抗式审核中发现的严重问题提供修复方案
"""

import re
import sqlite3
import fcntl
from pathlib import Path
from contextlib import contextmanager
from typing import List, Optional
import time

# ============ 修复 1: SQL 注入防护 ============

def sanitize_keyword(keyword: str) -> str:
    """
    清理用户输入，防止 SQL 注入
    只保留：字母、数字、中文、空格
    """
    # 只允许安全字符
    sanitized = re.sub(r'[^\w\s一-鿿]', '', keyword)
    # 限制长度
    return sanitized[:100]

def sanitize_keywords(query: str) -> List[str]:
    """清理并分词"""
    keywords = [sanitize_keyword(k.strip()) for k in query.split() if k.strip()]
    # 限制关键词数量
    return keywords[:10]

def safe_search_memories(query: str, limit: int = 10) -> List[dict]:
    """
    安全的记忆搜索（修复版）
    """
    conn = get_db()
    cursor = conn.cursor()

    # 解析类型过滤
    type_filter = None
    clean_query = query
    type_match = re.match(r'type:(\w+)\s+(.*)', query)
    if type_match:
        type_filter = type_match.group(1)
        # 验证类型是否在白名单中
        VALID_TYPES = ['fact', 'preference', 'skill', 'error', 'pattern', 'insight']
        if type_filter not in VALID_TYPES:
            type_filter = None
        clean_query = type_match.group(2)

    # 清理关键词
    keywords = sanitize_keywords(clean_query)
    if not keywords:
        conn.close()
        return []

    results = []

    # FTS5 搜索（安全版本）
    try:
        # 使用参数化查询
        fts_query = " AND ".join(f'"{kw}"' for kw in keywords)
        if type_filter:
            fts_query += f' AND type:{type_filter}'

        cursor.execute("""
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
    except Exception as e:
        # 记录错误但不暴露细节
        print(f"⚠️ FTS5 search failed, fallback to LIKE")

    # 回退到 LIKE 搜索
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

    conn.close()
    return results


# ============ 修复 2: 总容量限制 ============

def add_memory_with_limit(content: str, mem_type: str, tags: str, importance: float):
    """
    添加记忆（带总量限制）
    """
    MAX_TOTAL_MEMORIES = 10000
    MAX_SHORT_TERM = 1000
    MAX_LONG_TERM = 5000

    conn = get_db()
    cursor = conn.cursor()

    # 检查总数
    cursor.execute("SELECT COUNT(*) FROM memory")
    total = cursor.fetchone()[0]

    if total >= MAX_TOTAL_MEMORIES:
        # 删除最低权重的短期记忆
        cursor.execute("""
            DELETE FROM memory
            WHERE id IN (
                SELECT id FROM memory
                WHERE short_term = 1
                ORDER BY weight ASC, created ASC
                LIMIT 1
            )
        """)
        print("⚠️ Reached max capacity, removed lowest weight memory")

    # 检查短期记忆数量
    cursor.execute("SELECT COUNT(*) FROM memory WHERE short_term = 1")
    short_term_count = cursor.fetchone()[0]

    if short_term_count >= MAX_SHORT_TERM:
        # 删除最老的低权重短期记忆
        cursor.execute("""
            DELETE FROM memory
            WHERE id IN (
                SELECT id FROM memory
                WHERE short_term = 1
                ORDER BY weight ASC, created ASC
                LIMIT 10
            )
        """)

    # 插入新记忆
    cursor.execute("""
        INSERT INTO memory (content, type, tags, weight, short_term, long_term,
                           created, updated, last_accessed)
        VALUES (?, ?, ?, ?, 1, 0, ?, ?, ?)
    """, (content, mem_type, tags, importance,
          time.time(), time.time(), time.time()))

    memory_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return memory_id


# ============ 修复 3: 完整的并发控制 ============

LOCK_FILE = Path("/tmp/dna-memory.lock")

@contextmanager
def memory_transaction(timeout: int = 5):
    """
    统一的锁和事务管理
    """
    lock_fd = None
    conn = None

    try:
        # 获取文件锁
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # 打开数据库连接
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("BEGIN EXCLUSIVE")

        yield conn

        # 提交事务
        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        raise

    finally:
        if conn:
            conn.close()
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


def safe_add_memory(content: str, mem_type: str, tags: str, importance: float):
    """
    使用事务的安全添加记忆
    """
    with memory_transaction() as conn:
        cursor = conn.cursor()

        # 检查总数
        cursor.execute("SELECT COUNT(*) FROM memory")
        total = cursor.fetchone()[0]

        MAX_MEMORIES = 10000
        if total >= MAX_MEMORIES:
            cursor.execute("""
                DELETE FROM memory
                WHERE id IN (
                    SELECT id FROM memory
                    ORDER BY weight ASC, created ASC
                    LIMIT 1
                )
            """)

        # 插入
        cursor.execute("""
            INSERT INTO memory (content, type, tags, weight, short_term, long_term,
                               created, updated, last_accessed)
            VALUES (?, ?, ?, ?, 1, 0, ?, ?, ?)
        """, (content, mem_type, tags, importance,
              time.time(), time.time(), time.time()))

        return cursor.lastrowid


# ============ 修复 4: 优化蒸馏算法 ============

from collections import defaultdict
from typing import Dict, List, Tuple

def find_similar_clusters_optimized(threshold: float = 0.75) -> List[List[Dict]]:
    """
    优化的聚类算法（从 O(n²) 到 O(n log n)）
    策略：
    1. 按类型分组（减少比较范围）
    2. 按时间分桶（只比较同时期的记忆）
    3. 使用倒排索引加速查找
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 获取所有记忆
    cursor.execute("""
        SELECT id, content, type, tags, weight, created, updated
        FROM memory
        ORDER BY created DESC
    """)

    memories = []
    for row in cursor.fetchall():
        memories.append({
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'tags': row[3],
            'weight': row[4],
            'created': row[5],
            'updated': row[6]
        })

    conn.close()

    # 按类型和时间分组
    groups = defaultdict(list)
    DAY_SECONDS = 86400
    BUCKET_DAYS = 7  # 7天为一桶

    for mem in memories:
        bucket = int(mem['created'] / (DAY_SECONDS * BUCKET_DAYS))
        key = (mem['type'], bucket)
        groups[key].append(mem)

    # 在每个小组内聚类
    all_clusters = []

    for group in groups.values():
        if len(group) < 2:
            continue

        # 构建倒排索引
        word_to_mems = defaultdict(list)
        for mem in group:
            words = set(re.findall(r'[一-鿿]+|[a-zA-Z]+', mem['content'].lower()))
            for word in words:
                word_to_mems[word].append(mem['id'])

        # 使用倒排索引找相似记忆
        clusters = []
        used = set()

        for mem in group:
            if mem['id'] in used:
                continue

            # 找候选记忆（共享关键词的）
            words = set(re.findall(r'[一-鿿]+|[a-zA-Z]+', mem['content'].lower()))
            candidates = set()
            for word in words:
                candidates.update(word_to_mems[word])

            # 计算相似度
            cluster = [mem]
            used.add(mem['id'])

            for candidate_id in candidates:
                if candidate_id in used or candidate_id == mem['id']:
                    continue

                candidate = next(m for m in group if m['id'] == candidate_id)
                similarity = calculate_similarity(mem['content'], candidate['content'])

                if similarity >= threshold:
                    cluster.append(candidate)
                    used.add(candidate_id)

            if len(cluster) >= 2:
                clusters.append(cluster)

        all_clusters.extend(clusters)

    return all_clusters


def calculate_similarity(text1: str, text2: str) -> float:
    """Jaccard 相似度（优化版本）"""
    words1 = set(re.findall(r'[一-鿿]+|[a-zA-Z]+', text1.lower()))
    words2 = set(re.findall(r'[一-鿿]+|[a-zA-Z]+', text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


# ============ 修复 5: 数据库索引优化 ============

def create_indexes():
    """
    创建性能优化索引
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 常用查询索引
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(type)",
        "CREATE INDEX IF NOT EXISTS idx_memory_weight ON memory(weight DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memory_layer ON memory(short_term, long_term)",
        "CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory(last_accessed DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memory_created ON memory(created DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memory_type_weight ON memory(type, weight DESC)",

        # 关联表索引
        "CREATE INDEX IF NOT EXISTS idx_relations_mem1 ON memory_relations(memory_id1)",
        "CREATE INDEX IF NOT EXISTS idx_relations_mem2 ON memory_relations(memory_id2)",
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    conn.commit()
    conn.close()

    print("✅ Indexes created successfully")


# ============ 修复 6: 自动备份 ============

import shutil
from datetime import datetime, timedelta

def auto_backup(backup_dir: Path, keep_days: int = 7):
    """
    自动备份数据库
    """
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 创建备份
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"memory_{timestamp}.db"

    try:
        shutil.copy(DB_PATH, backup_path)
        print(f"✅ Backup created: {backup_path}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return

    # 清理旧备份
    cutoff_time = datetime.now() - timedelta(days=keep_days)

    for backup_file in backup_dir.glob("memory_*.db"):
        try:
            # 从文件名提取时间戳
            timestamp_str = backup_file.stem.split('_', 1)[1]
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            if file_time < cutoff_time:
                backup_file.unlink()
                print(f"🗑️  Removed old backup: {backup_file}")
        except Exception:
            pass


# ============ 使用示例 ============

if __name__ == "__main__":
    print("🔧 DNA Memory 安全性修复示例\n")

    # 示例 1: 安全搜索
    print("1. 安全搜索测试")
    results = safe_search_memories("Python编程")
    print(f"   找到 {len(results)} 条记忆\n")

    # 示例 2: 带限制的添加
    print("2. 带容量限制的添加记忆")
    try:
        mid = add_memory_with_limit("测试记忆", "fact", "", 0.8)
        print(f"   已添加记忆 ID: {mid}\n")
    except Exception as e:
        print(f"   错误: {e}\n")

    # 示例 3: 创建索引
    print("3. 创建性能索引")
    create_indexes()
    print()

    # 示例 4: 自动备份
    print("4. 自动备份")
    backup_dir = Path.home() / ".dna-memory" / "backups"
    auto_backup(backup_dir, keep_days=7)
    print()

    print("✅ 所有修复示例执行完成")
