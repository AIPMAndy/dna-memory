#!/usr/bin/env python3
"""
Memory Graph - 记忆关联图谱增强
功能：
- 自动发现记忆关联
- 因果关系识别
- 矛盾检测
- 知识图谱可视化
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse
import re

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"

# 关联类型
RELATION_TYPES = {
    'related': '相关',
    'causes': '导致',
    'contradicts': '矛盾',
    'extends': '扩展',
    'supersedes': '替代'
}

# 相似度阈值
SIMILARITY_THRESHOLD = 0.6


# ============ 文本相似度 ============
def simple_similarity(text1: str, text2: str) -> float:
    """简单的文本相似度计算（基于词重叠）"""
    # 分词
    words1 = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text1.lower()))
    words2 = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text2.lower()))
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard 相似度
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


# ============ 关联发现 ============
def find_similar_memories(memory: Dict, conn: sqlite3.Connection, threshold: float = 0.6) -> List[Tuple[Dict, float]]:
    """找到相似的记忆"""
    cursor = conn.cursor()
    
    # 获取所有其他记忆
    cursor.execute("""
        SELECT id, content, type, tags, weight, created
        FROM memory
        WHERE id != ?
    """, (memory['id'],))
    
    similar = []
    for row in cursor.fetchall():
        other = {
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'tags': row[3],
            'weight': row[4],
            'created': row[5]
        }
        
        similarity = simple_similarity(memory['content'], other['content'])
        
        if similarity >= threshold:
            similar.append((other, similarity))
    
    # 按相似度排序
    similar.sort(key=lambda x: x[1], reverse=True)
    
    return similar


def detect_causal_relation(memory1: Dict, memory2: Dict) -> Optional[str]:
    """检测因果关系"""
    content1 = memory1['content'].lower()
    content2 = memory2['content'].lower()
    
    # 错误 → 解决方案
    if memory1['type'] == 'error' and memory2['type'] in ['skill', 'fact']:
        # 检查是否包含相关关键词
        error_keywords = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', content1))
        solution_keywords = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', content2))
        
        overlap = len(error_keywords & solution_keywords)
        if overlap >= 2:
            return 'causes'  # memory1 导致需要 memory2
    
    # 因果关键词
    causal_patterns = [
        (r'因为.*所以', 'causes'),
        (r'导致', 'causes'),
        (r'原因.*结果', 'causes')
    ]
    
    for pattern, relation in causal_patterns:
        if re.search(pattern, content1) or re.search(pattern, content2):
            return relation
    
    return None


def detect_contradiction(memory1: Dict, memory2: Dict) -> bool:
    """检测矛盾"""
    content1 = memory1['content'].lower()
    content2 = memory2['content'].lower()
    
    # 同类型的偏好可能矛盾
    if memory1['type'] == 'preference' and memory2['type'] == 'preference':
        # 检查否定词
        negative_words = ['不要', '避免', '禁止', '不喜欢', '不用']
        positive_words = ['要', '使用', '喜欢', '推荐']
        
        has_negative_1 = any(word in content1 for word in negative_words)
        has_negative_2 = any(word in content2 for word in negative_words)
        
        # 一个肯定一个否定，且内容相似
        if has_negative_1 != has_negative_2:
            similarity = simple_similarity(content1, content2)
            if similarity > 0.5:
                return True
    
    return False


def auto_discover_relations(memory_id: int, conn: sqlite3.Connection) -> List[Dict]:
    """自动发现记忆关联"""
    cursor = conn.cursor()
    
    # 获取目标记忆
    cursor.execute("""
        SELECT id, content, type, tags, weight, created
        FROM memory
        WHERE id = ?
    """, (memory_id,))
    
    row = cursor.fetchone()
    if not row:
        return []
    
    memory = {
        'id': row[0],
        'content': row[1],
        'type': row[2],
        'tags': row[3],
        'weight': row[4],
        'created': row[5]
    }
    
    discovered = []
    
    # 1. 找相似记忆
    similar = find_similar_memories(memory, conn, threshold=SIMILARITY_THRESHOLD)
    
    for other, similarity in similar:
        # 检查是否已存在关联
        cursor.execute("""
            SELECT COUNT(*) FROM memory_relations
            WHERE (memory_id1 = ? AND memory_id2 = ?)
               OR (memory_id1 = ? AND memory_id2 = ?)
        """, (memory_id, other['id'], other['id'], memory_id))
        
        if cursor.fetchone()[0] > 0:
            continue  # 已存在
        
        # 2. 检测关系类型
        relation_type = 'related'
        
        # 因果关系
        causal = detect_causal_relation(memory, other)
        if causal:
            relation_type = causal
        
        # 矛盾关系
        if detect_contradiction(memory, other):
            relation_type = 'contradicts'
        
        # 3. 创建关联
        cursor.execute("""
            INSERT INTO memory_relations (memory_id1, memory_id2, relation_type, weight)
            VALUES (?, ?, ?, ?)
        """, (memory_id, other['id'], relation_type, similarity))
        
        discovered.append({
            'from_id': memory_id,
            'to_id': other['id'],
            'relation_type': relation_type,
            'similarity': similarity
        })
    
    conn.commit()
    
    return discovered


def batch_discover_relations(limit: int = 100) -> Dict:
    """批量发现关联"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取最近更新的记忆
    cursor.execute("""
        SELECT id FROM memory
        ORDER BY updated DESC
        LIMIT ?
    """, (limit,))
    
    memory_ids = [row[0] for row in cursor.fetchall()]
    
    total_discovered = 0
    results = []
    
    for memory_id in memory_ids:
        discovered = auto_discover_relations(memory_id, conn)
        total_discovered += len(discovered)
        if discovered:
            results.append({
                'memory_id': memory_id,
                'discovered': discovered
            })
    
    conn.close()
    
    return {
        'total_memories': len(memory_ids),
        'total_relations': total_discovered,
        'results': results
    }


# ============ 关联查询 ============
def get_memory_graph(memory_id: int, depth: int = 2) -> Dict:
    """获取记忆关联图谱"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取中心记忆
    cursor.execute("""
        SELECT id, content, type, tags, weight
        FROM memory
        WHERE id = ?
    """, (memory_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {'error': '记忆不存在'}
    
    center = {
        'id': row[0],
        'content': row[1],
        'type': row[2],
        'tags': row[3],
        'weight': row[4]
    }
    
    # BFS 遍历关联
    visited = {memory_id}
    queue = [(memory_id, 0)]
    nodes = [center]
    edges = []
    
    while queue:
        current_id, current_depth = queue.pop(0)
        
        if current_depth >= depth:
            continue
        
        # 获取关联
        cursor.execute("""
            SELECT memory_id2, relation_type, weight
            FROM memory_relations
            WHERE memory_id1 = ?
        """, (current_id,))
        
        for row in cursor.fetchall():
            related_id = row[0]
            relation_type = row[1]
            relation_weight = row[2]
            
            edges.append({
                'from': current_id,
                'to': related_id,
                'type': relation_type,
                'weight': relation_weight
            })
            
            if related_id not in visited:
                visited.add(related_id)
                queue.append((related_id, current_depth + 1))
                
                # 获取节点信息
                cursor.execute("""
                    SELECT id, content, type, tags, weight
                    FROM memory
                    WHERE id = ?
                """, (related_id,))
                
                node_row = cursor.fetchone()
                if node_row:
                    nodes.append({
                        'id': node_row[0],
                        'content': node_row[1],
                        'type': node_row[2],
                        'tags': node_row[3],
                        'weight': node_row[4]
                    })
    
    conn.close()
    
    return {
        'center': center,
        'nodes': nodes,
        'edges': edges,
        'total_nodes': len(nodes),
        'total_edges': len(edges)
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Memory Graph - 记忆关联图谱')
    parser.add_argument('action', choices=['discover', 'graph', 'batch'], help='操作类型')
    parser.add_argument('--id', type=int, help='记忆 ID')
    parser.add_argument('--depth', type=int, default=2, help='图谱深度')
    parser.add_argument('--limit', type=int, default=100, help='批量处理数量')
    
    args = parser.parse_args()
    
    if args.action == 'discover':
        if not args.id:
            print("❌ 需要指定 --id")
            return
        
        conn = sqlite3.connect(str(DB_PATH))
        discovered = auto_discover_relations(args.id, conn)
        conn.close()
        
        print(f"✅ 为记忆 {args.id} 发现了 {len(discovered)} 个关联\n")
        for rel in discovered:
            print(f"  → [{rel['relation_type']}] 记忆 {rel['to_id']} (相似度: {rel['similarity']:.2f})")
    
    elif args.action == 'batch':
        result = batch_discover_relations(limit=args.limit)
        
        print(f"✅ 批量处理了 {result['total_memories']} 条记忆")
        print(f"   发现了 {result['total_relations']} 个新关联\n")
        
        for item in result['results'][:10]:
            print(f"记忆 {item['memory_id']}: {len(item['discovered'])} 个关联")
    
    elif args.action == 'graph':
        if not args.id:
            print("❌ 需要指定 --id")
            return
        
        graph = get_memory_graph(args.id, depth=args.depth)
        
        if 'error' in graph:
            print(f"❌ {graph['error']}")
            return
        
        print(f"📊 记忆 {args.id} 的关联图谱\n")
        print(f"中心记忆: {graph['center']['content'][:80]}...")
        print(f"节点数: {graph['total_nodes']}")
        print(f"边数: {graph['total_edges']}\n")
        
        print("关联关系:")
        for edge in graph['edges'][:20]:
            print(f"  {edge['from']} --[{edge['type']}]--> {edge['to']} (权重: {edge['weight']:.2f})")


if __name__ == '__main__':
    main()
