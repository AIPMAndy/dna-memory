#!/usr/bin/env python3
"""
增强版 Recall
支持上下文感知、时间相关性、智能排序
"""

import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path

class EnhancedRecall:
    """增强版 Recall"""
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def smart_recall(self, query, context=None, limit=10):
        """智能 Recall
        
        Args:
            query: 查询关键词
            context: 上下文信息（可选）
            limit: 返回结果数量
        
        Returns:
            记忆列表
        """
        results = []
        
        # 1. 基础 FTS5 搜索
        basic_results = self._fts5_search(query, limit=limit*2)
        results.extend(basic_results)
        
        # 2. 上下文增强
        if context:
            context_results = self._context_search(query, context, limit=limit)
            results.extend(context_results)
        
        # 3. 时间相关性
        time_results = self._time_aware_search(query, limit=limit)
        results.extend(time_results)
        
        # 4. 去重 + 排序
        results = self._dedupe_and_rank(results, limit=limit)
        
        # 5. 更新 recall 统计
        self._update_recall_stats([r['id'] for r in results])
        
        return results
    
    def _fts5_search(self, query, limit=20):
        """FTS5 全文搜索"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 尝试 FTS5 搜索
            cursor.execute("""
                SELECT m.id, m.content, m.type, m.weight, m.created
                FROM memory m
                JOIN memory_fts ON m.id = memory_fts.rowid
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = cursor.fetchall()
        except sqlite3.OperationalError:
            # FTS5 不可用，回退到 LIKE 搜索
            cursor.execute("""
                SELECT id, content, type, weight, created
                FROM memory
                WHERE content LIKE ?
                ORDER BY weight DESC
                LIMIT ?
            """, (f'%{query}%', limit))
            
            results = cursor.fetchall()
        
        conn.close()
        
        return [{
            'id': r[0],
            'content': r[1],
            'type': r[2],
            'weight': r[3],
            'created': r[4],
            'score': 1.0,
            'source': 'fts5',
        } for r in results]
    
    def _context_search(self, query, context, limit=10):
        """上下文增强搜索"""
        # 从 context 中提取关键词
        keywords = self._extract_keywords(context)
        
        if not keywords:
            return []
        
        # 用关键词扩展搜索
        expanded_query = f"{query} {' '.join(keywords[:3])}"
        
        results = self._fts5_search(expanded_query, limit=limit)
        
        # 降低置信度（因为是扩展搜索）
        for r in results:
            r['score'] = 0.8
            r['source'] = 'context'
        
        return results
    
    def _time_aware_search(self, query, limit=10):
        """时间相关性搜索"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近 7 天的记忆权重提升
        seven_days_ago = (datetime.now() - timedelta(days=7)).timestamp()
        
        cursor.execute("""
            SELECT id, content, type, weight, created
            FROM memory
            WHERE created > ?
              AND content LIKE ?
            ORDER BY weight DESC
            LIMIT ?
        """, (seven_days_ago, f'%{query}%', limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'content': r[1],
            'type': r[2],
            'weight': r[3],
            'created': r[4],
            'score': 1.2,  # 最近记忆加权
            'source': 'time_aware',
        } for r in results]
    
    def _extract_keywords(self, context):
        """从上下文中提取关键词"""
        if not context:
            return []
        
        # 简单实现：提取中文词汇（2-4 字）
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,4}', context)
        
        # 去重 + 限制数量
        return list(set(keywords))[:5]
    
    def _dedupe_and_rank(self, results, limit=10):
        """去重 + 排序"""
        seen = set()
        deduped = []
        
        for r in results:
            if r['id'] not in seen:
                seen.add(r['id'])
                deduped.append(r)
        
        # 按 weight * score 排序
        deduped.sort(key=lambda x: x['weight'] * x.get('score', 1.0), reverse=True)
        
        return deduped[:limit]
    
    def _update_recall_stats(self, memory_ids):
        """更新 recall 统计"""
        if not memory_ids:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否有 recall_count 字段
        cursor.execute("PRAGMA table_info(memory)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'recall_count' not in columns:
            # 添加字段
            cursor.execute("ALTER TABLE memory ADD COLUMN recall_count INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE memory ADD COLUMN last_recalled REAL")
        
        # 更新统计
        now = datetime.now().timestamp()
        for mem_id in memory_ids:
            cursor.execute("""
                UPDATE memory 
                SET recall_count = COALESCE(recall_count, 0) + 1,
                    last_recalled = ?
                WHERE id = ?
            """, (now, mem_id))
        
        conn.commit()
        conn.close()
    
    def recall_by_type(self, mem_type, limit=10):
        """按类型 recall"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, content, type, weight, created
            FROM memory
            WHERE type = ?
            ORDER BY weight DESC
            LIMIT ?
        """, (mem_type, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'content': r[1],
            'type': r[2],
            'weight': r[3],
            'created': r[4],
        } for r in results]
    
    def recall_recent(self, days=7, limit=10):
        """recall 最近的记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).timestamp()
        
        cursor.execute("""
            SELECT id, content, type, weight, created
            FROM memory
            WHERE created > ?
            ORDER BY created DESC
            LIMIT ?
        """, (since, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'content': r[1],
            'type': r[2],
            'weight': r[3],
            'created': r[4],
        } for r in results]


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版 Recall')
    parser.add_argument('query', nargs='?', help='查询关键词')
    parser.add_argument('--db', default='~/.openclaw/skills/dna-memory/memory/memory.db',
                        help='数据库路径')
    parser.add_argument('--context', help='上下文信息')
    parser.add_argument('--type', help='按类型过滤')
    parser.add_argument('--recent', type=int, help='最近 N 天')
    parser.add_argument('--limit', type=int, default=10, help='返回结果数量')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    recall = EnhancedRecall(str(db_path))
    
    if args.type:
        # 按类型 recall
        results = recall.recall_by_type(args.type, limit=args.limit)
    elif args.recent:
        # recall 最近的记忆
        results = recall.recall_recent(days=args.recent, limit=args.limit)
    elif args.query:
        # 智能 recall
        results = recall.smart_recall(args.query, context=args.context, limit=args.limit)
    else:
        print("❌ 请指定查询关键词、类型或时间范围")
        return
    
    if not results:
        print("❌ 没有找到相关记忆")
        return
    
    print(f"🔍 找到 {len(results)} 条记忆：")
    for r in results:
        weight = r.get('weight', 0)
        mem_type = r.get('type', 'unknown')
        content = r.get('content', '')
        
        # 格式化时间
        created = r.get('created')
        if created:
            created_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d')
        else:
            created_str = 'unknown'
        
        print(f"  [{weight:.2f}|{mem_type}|{created_str}] {content[:80]}...")


if __name__ == '__main__':
    main()
