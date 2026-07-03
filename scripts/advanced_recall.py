#!/usr/bin/env python3
"""
Advanced Recall - 增强版记忆召回
支持：
- 中文分词优化
- 混合检索（FTS5 + 语义）
- 智能重排序
- 上下文感知
"""

import json
import sqlite3
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import argparse

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"

# 中文分词正则（简单版，可扩展为 jieba）
CHINESE_WORD_PATTERN = re.compile(r'[\u4e00-\u9fff]+')
ENGLISH_WORD_PATTERN = re.compile(r'[a-zA-Z]+')


# ============ 中文分词 ============
def simple_chinese_tokenize(text: str) -> List[str]:
    """简单中文分词（基于正则，可扩展为 jieba）"""
    tokens = []
    
    # 提取中文词
    chinese_words = CHINESE_WORD_PATTERN.findall(text)
    for word in chinese_words:
        # 2-3 字切分
        if len(word) >= 2:
            for i in range(len(word) - 1):
                tokens.append(word[i:i+2])
        if len(word) >= 3:
            for i in range(len(word) - 2):
                tokens.append(word[i:i+3])
    
    # 提取英文词
    english_words = ENGLISH_WORD_PATTERN.findall(text.lower())
    tokens.extend(english_words)
    
    return list(set(tokens))  # 去重


def calculate_term_frequency(text: str, query_tokens: List[str]) -> float:
    """计算词频匹配度"""
    text_lower = text.lower()
    matches = sum(1 for token in query_tokens if token in text_lower)
    return matches / len(query_tokens) if query_tokens else 0.0


# ============ 相关性评分 ============
def calculate_relevance_score(
    memory: Dict,
    query: str,
    query_tokens: List[str],
    context: Optional[str] = None
) -> float:
    """计算记忆与查询的相关性得分"""
    score = 0.0
    
    # 1. 词频匹配（40%）
    content = memory.get('content', '')
    tf_score = calculate_term_frequency(content, query_tokens)
    score += tf_score * 0.4
    
    # 2. 完整匹配加成（20%）
    if query.lower() in content.lower():
        score += 0.2
    
    # 3. 权重加成（15%）
    weight = memory.get('weight', 0.5)
    score += weight * 0.15
    
    # 4. 时间新鲜度（10%）
    created = memory.get('created', time.time())
    days_old = (time.time() - created) / 86400
    freshness = max(0, 1 - days_old / 365)
    score += freshness * 0.1
    
    # 5. 类型匹配（10%）
    # 如果查询中包含类型关键词，优先返回该类型
    type_keywords = {
        'error': ['错误', '失败', '问题', 'error', 'fail'],
        'skill': ['技能', '方法', '如何', 'skill', 'how'],
        'preference': ['偏好', '喜欢', '习惯', 'prefer', 'like'],
        'pattern': ['模式', '规律', '经常', 'pattern', 'often']
    }
    memory_type = memory.get('type', 'fact')
    for type_name, keywords in type_keywords.items():
        if memory_type == type_name and any(kw in query.lower() for kw in keywords):
            score += 0.1
            break
    
    # 6. 上下文相关性（5%）
    if context:
        context_tokens = simple_chinese_tokenize(context)
        context_match = calculate_term_frequency(content, context_tokens)
        score += context_match * 0.05
    
    return min(score, 1.0)  # 限制在 [0, 1]


# ============ 混合检索 ============
def fts5_search(conn: sqlite3.Connection, query: str, limit: int = 20) -> List[Dict]:
    """FTS5 全文搜索"""
    cursor = conn.cursor()
    
    # 尝试 FTS5
    try:
        # 处理查询词
        query_clean = query.replace('"', '').replace("'", "")
        
        cursor.execute("""
            SELECT m.id, m.content, m.type, m.tags, m.weight, m.created, m.updated
            FROM memory m
            JOIN memory_fts fts ON m.id = fts.rowid
            WHERE memory_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query_clean, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'content': row[1],
                'type': row[2],
                'tags': row[3],
                'weight': row[4],
                'created': row[5],
                'updated': row[6]
            })
        return results
    except Exception:
        # FTS5 不可用，回退到 LIKE
        return like_search(conn, query, limit)


def like_search(conn: sqlite3.Connection, query: str, limit: int = 20) -> List[Dict]:
    """LIKE 搜索（FTS5 不可用时的回退方案）"""
    cursor = conn.cursor()
    
    # 分词
    tokens = simple_chinese_tokenize(query)
    
    # 构建 LIKE 查询
    conditions = []
    params = []
    for token in tokens[:5]:  # 最多 5 个词
        conditions.append("(content LIKE ? OR tags LIKE ?)")
        params.extend([f'%{token}%', f'%{token}%'])
    
    if not conditions:
        conditions.append("1=1")
    
    where_clause = " OR ".join(conditions)
    
    cursor.execute(f"""
        SELECT id, content, type, tags, weight, created, updated
        FROM memory
        WHERE {where_clause}
        ORDER BY weight DESC, updated DESC
        LIMIT ?
    """, params + [limit])
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'tags': row[3],
            'weight': row[4],
            'created': row[5],
            'updated': row[6]
        })
    return results


def advanced_recall(
    query: str,
    context: Optional[str] = None,
    type_filter: Optional[str] = None,
    limit: int = 10,
    min_score: float = 0.3
) -> List[Dict]:
    """增强版 Recall"""
    conn = sqlite3.connect(str(DB_PATH))
    
    # 1. FTS5 全文搜索（快速过滤）
    candidates = fts5_search(conn, query, limit=limit * 3)
    
    # 2. 类型过滤
    if type_filter:
        candidates = [m for m in candidates if m['type'] == type_filter]
    
    # 3. 分词
    query_tokens = simple_chinese_tokenize(query)
    
    # 4. 计算相关性得分
    scored_results = []
    for memory in candidates:
        score = calculate_relevance_score(memory, query, query_tokens, context)
        if score >= min_score:
            memory['relevance_score'] = score
            scored_results.append(memory)
    
    # 5. 重排序
    scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # 6. 更新访问记录（增加权重）
    cursor = conn.cursor()
    for memory in scored_results[:limit]:
        new_weight = min(memory['weight'] * 1.05, 1.0)
        cursor.execute("""
            UPDATE memory
            SET weight = ?, updated = ?
            WHERE id = ?
        """, (new_weight, time.time(), memory['id']))
    
    conn.commit()
    conn.close()
    
    return scored_results[:limit]


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Advanced Recall - 增强版记忆召回')
    parser.add_argument('query', help='搜索关键词')
    parser.add_argument('--context', '-c', help='上下文（提升相关性）')
    parser.add_argument('--type', '-t', help='类型过滤')
    parser.add_argument('--limit', '-l', type=int, default=10, help='返回数量')
    parser.add_argument('--min-score', type=float, default=0.3, help='最低相关性得分')
    
    args = parser.parse_args()
    
    results = advanced_recall(
        query=args.query,
        context=args.context,
        type_filter=args.type,
        limit=args.limit,
        min_score=args.min_score
    )
    
    if not results:
        print("❌ 没有找到相关记忆")
        return
    
    print(f"✅ 找到 {len(results)} 条相关记忆：\n")
    for i, memory in enumerate(results, 1):
        score = memory.get('relevance_score', 0)
        print(f"{i}. [ID:{memory['id']}] [{memory['type']}] 相关性:{score:.2f}")
        print(f"   {memory['content']}")
        print(f"   权重:{memory['weight']:.2f} | 标签:{memory['tags']}")
        print()


if __name__ == '__main__':
    main()
