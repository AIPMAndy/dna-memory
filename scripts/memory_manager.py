#!/usr/bin/env python3
"""
DNA Memory 管理界面 - 查看、编辑、删除记忆
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import json

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from path_utils import get_db_path


class MemoryManager:
    def __init__(self):
        self.db_path = get_db_path()
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    def list_memories(self, limit=20, offset=0, type_filter=None, min_weight=None):
        """列出记忆"""
        cursor = self.conn.cursor()

        query = "SELECT id, content, type, weight, last_accessed, created FROM memory WHERE 1=1"
        params = []

        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)

        if min_weight is not None:
            query += " AND weight >= ?"
            params.append(min_weight)

        query += " ORDER BY weight DESC, last_accessed DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return cursor.fetchall()

    def search_memories(self, keyword, limit=20):
        """搜索记忆"""
        cursor = self.conn.cursor()

        # FTS5 搜索
        cursor.execute("""
            SELECT m.id, m.content, m.type, m.weight, m.last_accessed
            FROM memory_fts fts
            JOIN memory m ON fts.rowid = m.id
            WHERE memory_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (keyword, limit))

        return cursor.fetchall()

    def get_memory(self, memory_id):
        """获取单个记忆详情"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, content, type, weight, tags,
                   created, last_accessed, recall_count,
                   short_term, long_term
            FROM memory
            WHERE id = ?
        """, (memory_id,))
        return cursor.fetchone()

    def update_memory(self, memory_id, content=None, type_=None, weight=None):
        """更新记忆"""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if type_ is not None:
            updates.append("type = ?")
            params.append(type_)

        if weight is not None:
            updates.append("weight = ?")
            params.append(weight)

        if not updates:
            return False

        params.append(memory_id)
        query = f"UPDATE memory SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()

        return cursor.rowcount > 0

    def delete_memory(self, memory_id):
        """删除记忆"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_statistics(self):
        """获取统计信息"""
        cursor = self.conn.cursor()

        # 总数
        cursor.execute("SELECT COUNT(*) FROM memory")
        total = cursor.fetchone()[0]

        # 按类型统计
        cursor.execute("""
            SELECT type, COUNT(*) as count, AVG(weight) as avg_weight
            FROM memory
            GROUP BY type
            ORDER BY count DESC
        """)
        by_type = cursor.fetchall()

        # 高优先级记忆
        cursor.execute("SELECT COUNT(*) FROM memory WHERE weight >= 0.8")
        high_priority = cursor.fetchone()[0]

        # 数据库大小
        db_size_mb = self.db_path.stat().st_size / (1024 * 1024)

        return {
            'total': total,
            'by_type': by_type,
            'high_priority': high_priority,
            'db_size_mb': round(db_size_mb, 2)
        }


def format_memory(memory, detailed=False):
    """格式化记忆显示"""
    content = memory['content'][:80] + '...' if len(memory['content']) > 80 else memory['content']

    output = f"ID: {memory['id']}\n"
    output += f"内容: {content}\n"
    output += f"类型: {memory['type']} | 权重: {memory['weight']:.2f}\n"

    if detailed:
        output += f"访问次数: {memory['recall_count'] if memory['recall_count'] else 0}\n"
        output += f"创建时间: {datetime.fromtimestamp(memory['created']).strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += f"最后访问: {datetime.fromtimestamp(memory['last_accessed']).strftime('%Y-%m-%d %H:%M:%S')}\n"
        if memory['short_term']:
            output += f"短期记忆: {'是' if memory['short_term'] else '否'}\n"
        if memory['long_term']:
            output += f"长期记忆: {'是' if memory['long_term'] else '否'}\n"

    return output


def main():
    import argparse

    parser = argparse.ArgumentParser(description='DNA Memory 管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出记忆')
    list_parser.add_argument('--type', help='按类型筛选')
    list_parser.add_argument('--min-weight', type=float, help='最低权重')
    list_parser.add_argument('--limit', type=int, default=20, help='数量限制')
    list_parser.add_argument('--offset', type=int, default=0, help='偏移量')

    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索记忆')
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--limit', type=int, default=20, help='数量限制')

    # view 命令
    view_parser = subparsers.add_parser('view', help='查看记忆详情')
    view_parser.add_argument('id', type=int, help='记忆ID')

    # update 命令
    update_parser = subparsers.add_parser('update', help='更新记忆')
    update_parser.add_argument('id', type=int, help='记忆ID')
    update_parser.add_argument('--content', help='新内容')
    update_parser.add_argument('--type', help='新类型')
    update_parser.add_argument('--weight', type=float, help='新权重')

    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除记忆')
    delete_parser.add_argument('id', type=int, help='记忆ID')
    delete_parser.add_argument('--confirm', action='store_true', help='确认删除')

    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='统计信息')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = MemoryManager()
    manager.connect()

    try:
        if args.command == 'list':
            memories = manager.list_memories(
                limit=args.limit,
                offset=args.offset,
                type_filter=args.type,
                min_weight=args.min_weight
            )

            if not memories:
                print("没有找到记忆")
                return

            print(f"共找到 {len(memories)} 条记忆:\n")
            for i, mem in enumerate(memories, 1):
                print(f"[{i}] " + "=" * 60)
                print(format_memory(mem))
                print()

        elif args.command == 'search':
            memories = manager.search_memories(args.keyword, args.limit)

            if not memories:
                print(f"没有找到包含 '{args.keyword}' 的记忆")
                return

            print(f"搜索 '{args.keyword}' 找到 {len(memories)} 条记忆:\n")
            for i, mem in enumerate(memories, 1):
                print(f"[{i}] " + "=" * 60)
                print(format_memory(mem))
                print()

        elif args.command == 'view':
            memory = manager.get_memory(args.id)

            if not memory:
                print(f"记忆 ID {args.id} 不存在")
                return

            print("=" * 70)
            print(format_memory(memory, detailed=True))
            print("=" * 70)
            print(f"\n完整内容:\n{memory['content']}")

        elif args.command == 'update':
            if not any([args.content, args.type, args.weight]):
                print("错误: 至少指定一个更新项 (--content, --type, --weight)")
                return

            success = manager.update_memory(
                args.id,
                content=args.content,
                type_=args.type,
                weight=args.weight
            )

            if success:
                print(f"✅ 记忆 ID {args.id} 已更新")
            else:
                print(f"❌ 记忆 ID {args.id} 不存在")

        elif args.command == 'delete':
            if not args.confirm:
                print(f"警告: 将删除记忆 ID {args.id}")
                print("添加 --confirm 参数以确认删除")
                return

            success = manager.delete_memory(args.id)

            if success:
                print(f"✅ 记忆 ID {args.id} 已删除")
            else:
                print(f"❌ 记忆 ID {args.id} 不存在")

        elif args.command == 'stats':
            stats = manager.get_statistics()

            print("📊 DNA Memory 统计信息")
            print("=" * 60)
            print(f"总记忆数: {stats['total']}")
            print(f"高优先级记忆 (≥0.8): {stats['high_priority']}")
            print(f"数据库大小: {stats['db_size_mb']} MB")
            print(f"\n按类型分布:")

            for row in stats['by_type']:
                print(f"  {row['type']:12s}: {row['count']:3d} 条 (平均权重: {row['avg_weight']:.2f})")

    finally:
        manager.close()


if __name__ == '__main__':
    main()
