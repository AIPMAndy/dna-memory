#!/usr/bin/env python3
"""
Memory Distillation - 记忆蒸馏系统
功能：
- 将多条相似记忆合并为一条高质量记忆
- 提取共同模式
- 删除冗余记忆
- 保留精华知识
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import re

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"

# 蒸馏参数
SIMILARITY_THRESHOLD = 0.75  # 相似度阈值
MIN_CLUSTER_SIZE = 2         # 最小簇大小


# ============ 文本相似度 ============
def calculate_similarity(text1: str, text2: str) -> float:
    """计算文本相似度（Jaccard）"""
    words1 = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text1.lower()))
    words2 = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text2.lower()))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


# ============ 聚类 ============
def find_similar_clusters(threshold: float = SIMILARITY_THRESHOLD) -> List[List[Dict]]:
    """找到相似记忆簇"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取所有记忆
    cursor.execute("""
        SELECT id, content, type, tags, weight, created, updated
        FROM memory
        ORDER BY weight DESC
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
    
    # 聚类
    clusters = []
    used = set()
    
    for i, mem1 in enumerate(memories):
        if mem1['id'] in used:
            continue
        
        cluster = [mem1]
        used.add(mem1['id'])
        
        for j, mem2 in enumerate(memories[i+1:], i+1):
            if mem2['id'] in used:
                continue
            
            # 计算相似度
            similarity = calculate_similarity(mem1['content'], mem2['content'])
            
            if similarity >= threshold:
                cluster.append(mem2)
                used.add(mem2['id'])
        
        # 只保留大小 >= MIN_CLUSTER_SIZE 的簇
        if len(cluster) >= MIN_CLUSTER_SIZE:
            clusters.append(cluster)
    
    return clusters


# ============ 模式提取 ============
def extract_common_pattern(cluster: List[Dict]) -> str:
    """提取共同模式"""
    # 简单策略：找到所有记忆中的共同词
    all_words = []
    for memory in cluster:
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', memory['content'])
        all_words.append(set(words))
    
    # 找交集
    common_words = set.intersection(*all_words) if all_words else set()
    
    if not common_words:
        # 如果没有共同词，取最长的记忆作为模式
        longest = max(cluster, key=lambda m: len(m['content']))
        return longest['content']
    
    # 构建模式描述
    # 优先使用权重最高的记忆作为模板
    template = max(cluster, key=lambda m: m['weight'])
    
    # 添加来源信息
    sources = [m['id'] for m in cluster]
    pattern = f"{template['content']} [蒸馏自 {len(cluster)} 条记忆: {sources}]"
    
    return pattern


# ============ 蒸馏 ============
def distill_cluster(cluster: List[Dict], dry_run: bool = True) -> Dict:
    """蒸馏一个记忆簇"""
    # 提取模式
    pattern = extract_common_pattern(cluster)
    
    # 计算新权重（取最大值）
    max_weight = max(m['weight'] for m in cluster)
    
    # 合并标签
    all_tags = set()
    for memory in cluster:
        if memory['tags']:
            all_tags.update(memory['tags'].split(','))
    merged_tags = ','.join(sorted(all_tags))
    
    # 确定类型（优先 pattern）
    types = [m['type'] for m in cluster]
    if 'pattern' in types:
        distilled_type = 'pattern'
    else:
        # 取最常见的类型
        distilled_type = max(set(types), key=types.count)
    
    distilled = {
        'content': pattern,
        'type': distilled_type,
        'tags': merged_tags,
        'weight': max_weight,
        'sources': [m['id'] for m in cluster]
    }
    
    if not dry_run:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 删除旧记忆
        for memory in cluster:
            cursor.execute("DELETE FROM memory WHERE id = ?", (memory['id'],))
        
        # 插入新记忆
        cursor.execute("""
            INSERT INTO memory (content, type, tags, weight, short_term, long_term)
            VALUES (?, ?, ?, ?, 0, 1)
        """, (distilled['content'], distilled['type'], distilled['tags'], distilled['weight']))
        
        new_id = cursor.lastrowid
        
        # 记录蒸馏操作
        cursor.execute("""
            INSERT INTO operations (operation, details)
            VALUES (?, ?)
        """, ('distill', json.dumps({
            'new_id': new_id,
            'sources': distilled['sources'],
            'cluster_size': len(cluster)
        })))
        
        conn.commit()
        conn.close()
        
        distilled['id'] = new_id
    
    return distilled


def batch_distill(threshold: float = SIMILARITY_THRESHOLD, dry_run: bool = True) -> List[Dict]:
    """批量蒸馏"""
    clusters = find_similar_clusters(threshold)
    
    results = []
    for cluster in clusters:
        distilled = distill_cluster(cluster, dry_run)
        results.append({
            'cluster_size': len(cluster),
            'distilled': distilled
        })
    
    return results


# ============ 统计 ============
def analyze_distillation_potential(threshold: float = SIMILARITY_THRESHOLD) -> Dict:
    """分析蒸馏潜力"""
    clusters = find_similar_clusters(threshold)
    
    total_memories = sum(len(cluster) for cluster in clusters)
    potential_savings = total_memories - len(clusters)
    
    return {
        'cluster_count': len(clusters),
        'total_memories': total_memories,
        'potential_savings': potential_savings,
        'compression_ratio': potential_savings / total_memories if total_memories > 0 else 0,
        'clusters': [
            {
                'size': len(cluster),
                'preview': cluster[0]['content'][:50] + '...'
            }
            for cluster in clusters
        ]
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Memory Distillation - 记忆蒸馏')
    parser.add_argument('action', choices=['analyze', 'distill'], help='操作类型')
    parser.add_argument('--threshold', type=float, default=SIMILARITY_THRESHOLD, help='相似度阈值')
    parser.add_argument('--dry-run', action='store_true', help='预览模式（不实际删除）')
    
    args = parser.parse_args()
    
    if args.action == 'analyze':
        stats = analyze_distillation_potential(threshold=args.threshold)
        
        print(f"\n📊 蒸馏潜力分析（相似度阈值: {args.threshold}）\n")
        print(f"发现簇数: {stats['cluster_count']}")
        print(f"涉及记忆数: {stats['total_memories']}")
        print(f"可节省记忆数: {stats['potential_savings']}")
        print(f"压缩率: {stats['compression_ratio']:.1%}")
        
        if stats['clusters']:
            print(f"\n前 10 个簇：")
            for i, cluster in enumerate(stats['clusters'][:10], 1):
                print(f"{i}. 大小: {cluster['size']} | {cluster['preview']}")
    
    elif args.action == 'distill':
        results = batch_distill(threshold=args.threshold, dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"\n🔍 预览模式：将蒸馏 {len(results)} 个簇\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. 簇大小: {result['cluster_size']}")
                print(f"   蒸馏后: {result['distilled']['content'][:80]}...")
                print(f"   来源: {result['distilled']['sources']}")
                print()
            
            print("\n使用 --no-dry-run 执行实际蒸馏")
        else:
            print(f"\n✅ 已蒸馏 {len(results)} 个簇\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. 簇大小: {result['cluster_size']} → 新记忆 ID: {result['distilled'].get('id')}")


if __name__ == '__main__':
    main()
