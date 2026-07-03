#!/usr/bin/env python3
"""
DNA Memory 性能优化脚本
解决记忆内容过多时的性能问题
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DNA_MEMORY_DB = Path.home() / ".cc-switch/skills/dna-memory/memory/memory.db"

def analyze_performance():
    """分析性能瓶颈"""
    conn = sqlite3.connect(str(DNA_MEMORY_DB))
    cursor = conn.cursor()

    print("📊 DNA Memory 性能分析")
    print("=" * 60)

    # 1. 数据库大小
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    db_size = cursor.fetchone()[0]
    print(f"数据库大小: {db_size / 1024:.2f} KB")

    # 2. 记忆数量
    cursor.execute("SELECT COUNT(*) FROM memory")
    total = cursor.fetchone()[0]
    print(f"总记忆数: {total}")

    # 3. 按类型统计
    cursor.execute("SELECT type, COUNT(*) FROM memory GROUP BY type")
    print("\n按类型分布:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # 4. 权重分布
    cursor.execute("""
        SELECT
            SUM(CASE WHEN weight >= 0.8 THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN weight >= 0.5 AND weight < 0.8 THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN weight < 0.5 THEN 1 ELSE 0 END) as low
        FROM memory
    """)
    high, medium, low = cursor.fetchone()
    print(f"\n权重分布:")
    print(f"  高权重 (≥0.8): {high}")
    print(f"  中权重 (0.5-0.8): {medium}")
    print(f"  低权重 (<0.5): {low}")

    # 5. 访问时间分布
    now = datetime.now().timestamp()
    cursor.execute("""
        SELECT
            SUM(CASE WHEN ? - last_accessed < 86400 THEN 1 ELSE 0 END) as day,
            SUM(CASE WHEN ? - last_accessed < 604800 THEN 1 ELSE 0 END) as week,
            SUM(CASE WHEN ? - last_accessed < 2592000 THEN 1 ELSE 0 END) as month,
            SUM(CASE WHEN ? - last_accessed >= 2592000 THEN 1 ELSE 0 END) as old
        FROM memory
    """, (now, now, now, now))
    day, week, month, old = cursor.fetchone()
    print(f"\n最后访问:")
    print(f"  24小时内: {day}")
    print(f"  7天内: {week}")
    print(f"  30天内: {month}")
    print(f"  超过30天: {old}")

    # 6. 检查索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    print(f"\n索引数量: {len(indexes)}")

    # 7. 性能建议
    print("\n" + "=" * 60)
    print("🔧 性能优化建议:")

    suggestions = []

    if total > 1000:
        suggestions.append(f"⚠️  记忆数量较多 ({total})，建议清理低权重记忆")

    if low > total * 0.3:
        suggestions.append(f"⚠️  低权重记忆过多 ({low})，建议删除")

    if old > total * 0.5:
        suggestions.append(f"⚠️  超过30天未访问的记忆过多 ({old})，建议归档")

    if len(indexes) < 3:
        suggestions.append("⚠️  缺少索引，建议添加")

    if db_size > 10 * 1024 * 1024:  # > 10MB
        suggestions.append(f"⚠️  数据库较大 ({db_size / 1024 / 1024:.2f} MB)，建议 VACUUM")

    if suggestions:
        for s in suggestions:
            print(f"  {s}")
    else:
        print("  ✅ 性能良好，无需优化")

    conn.close()

def add_indexes():
    """添加性能索引"""
    conn = sqlite3.connect(str(DNA_MEMORY_DB))
    cursor = conn.cursor()

    print("\n🔧 添加性能索引...")

    indexes = [
        ("idx_memory_weight", "CREATE INDEX IF NOT EXISTS idx_memory_weight ON memory(weight DESC)"),
        ("idx_memory_type", "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(type)"),
        ("idx_memory_last_accessed", "CREATE INDEX IF NOT EXISTS idx_memory_last_accessed ON memory(last_accessed DESC)"),
        ("idx_memory_short_term", "CREATE INDEX IF NOT EXISTS idx_memory_short_term ON memory(short_term)"),
        ("idx_memory_long_term", "CREATE INDEX IF NOT EXISTS idx_memory_long_term ON memory(long_term)"),
    ]

    for name, sql in indexes:
        try:
            cursor.execute(sql)
            print(f"  ✅ {name}")
        except sqlite3.OperationalError as e:
            print(f"  ⚠️  {name}: {e}")

    conn.commit()
    conn.close()
    print("✅ 索引添加完成")

def cleanup_low_weight(threshold=0.3, dry_run=True):
    """清理低权重记忆"""
    conn = sqlite3.connect(str(DNA_MEMORY_DB))
    cursor = conn.cursor()

    # 查找低权重记忆
    cursor.execute("""
        SELECT id, content, weight, type
        FROM memory
        WHERE weight < ?
        ORDER BY weight ASC
    """, (threshold,))

    low_weight = cursor.fetchall()

    print(f"\n🗑️  低权重记忆清理 (阈值: {threshold})")
    print("=" * 60)
    print(f"找到 {len(low_weight)} 条低权重记忆:")

    for row in low_weight[:10]:  # 只显示前10条
        print(f"  [{row[2]:.2f}|{row[3]}] {row[1][:60]}...")

    if len(low_weight) > 10:
        print(f"  ... 还有 {len(low_weight) - 10} 条")

    if dry_run:
        print("\n⚠️  预览模式，未实际删除")
        print(f"运行 `python3 scripts/performance_optimizer.py cleanup --threshold {threshold}` 执行删除")
    else:
        cursor.execute("DELETE FROM memory WHERE weight < ?", (threshold,))
        conn.commit()
        print(f"\n✅ 已删除 {len(low_weight)} 条低权重记忆")

    conn.close()

def archive_old_memories(days=90, dry_run=True):
    """归档超过N天未访问的记忆"""
    conn = sqlite3.connect(str(DNA_MEMORY_DB))
    cursor = conn.cursor()

    cutoff = datetime.now().timestamp() - (days * 86400)

    cursor.execute("""
        SELECT id, content, last_accessed, weight, type
        FROM memory
        WHERE last_accessed < ? AND weight < 0.8
        ORDER BY last_accessed ASC
    """, (cutoff,))

    old_memories = cursor.fetchall()

    print(f"\n📦 归档旧记忆 (超过 {days} 天未访问，权重 < 0.8)")
    print("=" * 60)
    print(f"找到 {len(old_memories)} 条旧记忆:")

    for row in old_memories[:10]:
        days_ago = (datetime.now().timestamp() - row[2]) / 86400
        print(f"  [{row[3]:.2f}|{row[4]}] {int(days_ago)}天前 - {row[1][:50]}...")

    if len(old_memories) > 10:
        print(f"  ... 还有 {len(old_memories) - 10} 条")

    if dry_run:
        print("\n⚠️  预览模式，未实际归档")
        print(f"运行 `python3 scripts/performance_optimizer.py archive --days {days}` 执行归档")
    else:
        # 标记为归档（long_term=1）
        ids = [row[0] for row in old_memories]
        cursor.executemany("UPDATE memory SET long_term=1 WHERE id=?", [(id,) for id in ids])
        conn.commit()
        print(f"\n✅ 已归档 {len(old_memories)} 条旧记忆")

    conn.close()

def vacuum_db():
    """压缩数据库"""
    print("\n🔧 压缩数据库...")

    conn = sqlite3.connect(str(DNA_MEMORY_DB))

    # 获取压缩前大小
    cursor = conn.cursor()
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    before_size = cursor.fetchone()[0]

    # 执行 VACUUM
    conn.execute("VACUUM")
    conn.commit()

    # 获取压缩后大小
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    after_size = cursor.fetchone()[0]

    saved = before_size - after_size
    saved_pct = (saved / before_size * 100) if before_size > 0 else 0

    print(f"  压缩前: {before_size / 1024:.2f} KB")
    print(f"  压缩后: {after_size / 1024:.2f} KB")
    print(f"  节省: {saved / 1024:.2f} KB ({saved_pct:.1f}%)")

    conn.close()
    print("✅ 数据库压缩完成")

def set_limits():
    """设置记忆数量限制"""
    conn = sqlite3.connect(str(DNA_MEMORY_DB))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM memory")
    total = cursor.fetchone()[0]

    print(f"\n⚙️  当前记忆数: {total}")
    print("\n推荐限制:")
    print("  短期记忆: 100 条")
    print("  长期记忆: 500 条")
    print("  总计上限: 1000 条")

    if total > 1000:
        print(f"\n⚠️  当前记忆数 ({total}) 超过推荐上限 (1000)")
        print("建议执行清理:")
        print("  1. 删除低权重记忆: cleanup --threshold 0.3")
        print("  2. 归档旧记忆: archive --days 90")

    conn.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DNA Memory 性能优化工具")
    parser.add_argument("action", nargs="?", default="analyze",
                       choices=["analyze", "index", "cleanup", "archive", "vacuum", "limits", "all"],
                       help="操作: analyze/index/cleanup/archive/vacuum/limits/all")
    parser.add_argument("--threshold", type=float, default=0.3, help="清理阈值 (默认 0.3)")
    parser.add_argument("--days", type=int, default=90, help="归档天数 (默认 90)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行")

    args = parser.parse_args()

    if args.action == "analyze":
        analyze_performance()
    elif args.action == "index":
        add_indexes()
    elif args.action == "cleanup":
        cleanup_low_weight(args.threshold, args.dry_run)
    elif args.action == "archive":
        archive_old_memories(args.days, args.dry_run)
    elif args.action == "vacuum":
        vacuum_db()
    elif args.action == "limits":
        set_limits()
    elif args.action == "all":
        analyze_performance()
        add_indexes()
        cleanup_low_weight(args.threshold, dry_run=True)
        archive_old_memories(args.days, dry_run=True)
        set_limits()
