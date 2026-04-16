#!/usr/bin/env python3
"""
思考型记忆（Thought-Based Memory）
不只存储原始内容，更存储提炼后的"思考"
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

class ThoughtMemory:
    """思考型记忆"""
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def remember_with_thought(self, raw_content, thought, mem_type='fact', confidence=0.8, source=None):
        """记录时同时存储原始内容和提炼后的思考
        
        Args:
            raw_content: 原始内容
            thought: 提炼后的思考（核心洞察）
            mem_type: 记忆类型
            confidence: 置信度
            source: 来源（对话ID、文档ID等）
        
        Returns:
            记忆ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在相似记忆
        cursor.execute("""
            SELECT id FROM memory 
            WHERE thought LIKE ? OR content LIKE ?
            LIMIT 1
        """, (f"%{thought[:50]}%", f"%{raw_content[:50]}%"))
        
        if cursor.fetchone():
            conn.close()
            return None  # 跳过重复记忆
        
        # 插入新记忆
        cursor.execute("""
            INSERT INTO memory (content, thought, type, weight, short_term, long_term, source, tags)
            VALUES (?, ?, ?, ?, 1, 0, ?, 'thought_based')
        """, (raw_content, thought, mem_type, confidence, source))
        
        memory_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return memory_id
    
    def recall_thought(self, query, limit=10):
        """优先检索思考，而不是原始内容
        
        Args:
            query: 查询关键词
            limit: 返回结果数量
        
        Returns:
            记忆列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 优先搜索 thought 字段，其次搜索 content
        cursor.execute("""
            SELECT id, content, thought, type, weight, source, created
            FROM memory
            WHERE thought LIKE ? OR content LIKE ?
            ORDER BY 
                CASE WHEN thought LIKE ? THEN 1 ELSE 2 END,  -- thought 匹配优先
                weight DESC
            LIMIT ?
        """, (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'content': r[1],
            'thought': r[2],
            'type': r[3],
            'weight': r[4],
            'source': r[5],
            'created': r[6],
        } for r in results]
    
    def extract_thought(self, content):
        """从原始内容中提取思考（简单实现）
        
        Args:
            content: 原始内容
        
        Returns:
            提炼后的思考
        """
        # 简单策略：提取关键句
        
        # 1. 如果包含"核心是"、"关键是"、"本质是"，提取后面的内容
        import re
        
        patterns = [
            r'核心是[：:](.*?)(?:[。，,]|$)',
            r'关键是[：:](.*?)(?:[。，,]|$)',
            r'本质是[：:](.*?)(?:[。，,]|$)',
            r'重点是[：:](.*?)(?:[。，,]|$)',
            r'问题是[：:](.*?)(?:[。，,]|$)',
            r'原因是[：:](.*?)(?:[。，,]|$)',
            r'结论是[：:](.*?)(?:[。，,]|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        
        # 2. 如果没有明确的关键句，取第一句话
        sentences = re.split(r'[。！？]', content)
        if sentences:
            return sentences[0].strip()
        
        # 3. 如果都没有，返回前 100 个字符
        return content[:100]
    
    def batch_add_thoughts(self, memories):
        """批量为已有记忆添加思考
        
        Args:
            memories: 记忆列表（包含 id 和 content）
        
        Returns:
            更新数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for mem in memories:
            mem_id = mem['id']
            content = mem['content']
            
            # 提取思考
            thought = self.extract_thought(content)
            
            # 更新记忆
            cursor.execute("""
                UPDATE memory
                SET thought = ?
                WHERE id = ?
            """, (thought, mem_id))
            
            count += 1
        
        conn.commit()
        conn.close()
        
        return count
    
    def get_memories_without_thought(self, limit=100):
        """获取没有思考的记忆
        
        Args:
            limit: 返回结果数量
        
        Returns:
            记忆列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, content, type, weight
            FROM memory
            WHERE thought IS NULL OR thought = ''
            ORDER BY weight DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'content': r[1],
            'type': r[2],
            'weight': r[3],
        } for r in results]


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='思考型记忆管理')
    parser.add_argument('action', choices=['remember', 'recall', 'extract', 'batch-add'],
                        help='操作类型')
    parser.add_argument('--db', default='~/.openclaw/skills/dna-memory/memory/memory.db',
                        help='数据库路径')
    parser.add_argument('--content', help='原始内容')
    parser.add_argument('--thought', help='提炼后的思考')
    parser.add_argument('--type', default='fact', help='记忆类型')
    parser.add_argument('--confidence', type=float, default=0.8, help='置信度')
    parser.add_argument('--source', help='来源')
    parser.add_argument('--query', help='查询关键词')
    parser.add_argument('--limit', type=int, default=10, help='返回结果数量')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    tm = ThoughtMemory(str(db_path))
    
    if args.action == 'remember':
        if not args.content:
            print("❌ 请指定 --content")
            return
        
        # 如果没有提供 thought，自动提取
        thought = args.thought or tm.extract_thought(args.content)
        
        memory_id = tm.remember_with_thought(
            args.content,
            thought,
            args.type,
            args.confidence,
            args.source
        )
        
        if memory_id:
            print(f"✅ 已记录（ID: {memory_id}）")
            print(f"  原始内容: {args.content[:80]}...")
            print(f"  提炼思考: {thought}")
        else:
            print("⚠️ 记忆已存在，跳过")
    
    elif args.action == 'recall':
        if not args.query:
            print("❌ 请指定 --query")
            return
        
        results = tm.recall_thought(args.query, args.limit)
        
        if not results:
            print("❌ 没有找到相关记忆")
            return
        
        print(f"🔍 找到 {len(results)} 条记忆：")
        for r in results:
            print(f"\n  [{r['weight']:.2f}|{r['type']}] ID: {r['id']}")
            print(f"  思考: {r['thought']}")
            print(f"  原文: {r['content'][:80]}...")
            if r['source']:
                print(f"  来源: {r['source']}")
    
    elif args.action == 'extract':
        if not args.content:
            print("❌ 请指定 --content")
            return
        
        thought = tm.extract_thought(args.content)
        print(f"💡 提炼思考: {thought}")
    
    elif args.action == 'batch-add':
        # 批量为已有记忆添加思考
        memories = tm.get_memories_without_thought(args.limit)
        
        if not memories:
            print("✅ 所有记忆都已有思考")
            return
        
        print(f"🔄 为 {len(memories)} 条记忆添加思考...")
        count = tm.batch_add_thoughts(memories)
        print(f"✅ 已更新 {count} 条记忆")


if __name__ == '__main__':
    main()
