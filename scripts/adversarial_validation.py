#!/usr/bin/env python3
"""
Adversarial Memory Validation - 对抗性记忆验证
功能：
- 主动寻找矛盾的记忆
- 验证哪个记忆是正确的
- 自动降低错误记忆的权重
- 建立替代关系
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse
import re

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"

# 矛盾检测阈值
CONTRADICTION_THRESHOLD = 0.6  # 内容相似但语义相反


# ============ 矛盾检测 ============
def detect_negation(text: str) -> bool:
    """检测否定词"""
    negation_words = [
        '不要', '不', '避免', '禁止', '不能', '不应该', '别',
        '不用', '不需要', '不建议', '不推荐',
        'not', 'no', 'never', 'avoid', 'don\'t', 'shouldn\'t'
    ]
    
    return any(word in text.lower() for word in negation_words)


def extract_core_concept(text: str) -> str:
    """提取核心概念（去除否定词）"""
    # 移除否定词
    negation_pattern = r'(不要|不|避免|禁止|不能|不应该|别|不用|不需要|not|no|never|avoid|don\'t|shouldn\'t)\s*'
    core = re.sub(negation_pattern, '', text, flags=re.IGNORECASE)
    
    return core.strip()


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """计算语义相似度（基于词重叠）"""
    words1 = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text1.lower()))
    words2 = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text2.lower()))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def find_contradictions() -> List[Tuple[Dict, Dict, float]]:
    """找到潜在矛盾的记忆对"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取所有记忆
    cursor.execute("""
        SELECT id, content, type, weight, created, updated
        FROM memory
        ORDER BY updated DESC
    """)
    
    memories = []
    for row in cursor.fetchall():
        memories.append({
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'weight': row[3],
            'created': row[4],
            'updated': row[5]
        })
    
    conn.close()
    
    contradictions = []
    
    for i, mem1 in enumerate(memories):
        for mem2 in memories[i+1:]:
            # 检测是否可能矛盾
            has_negation_1 = detect_negation(mem1['content'])
            has_negation_2 = detect_negation(mem2['content'])
            
            # 一个有否定，一个没有
            if has_negation_1 != has_negation_2:
                # 提取核心概念
                core1 = extract_core_concept(mem1['content'])
                core2 = extract_core_concept(mem2['content'])
                
                # 计算核心概念相似度
                similarity = calculate_semantic_similarity(core1, core2)
                
                if similarity >= CONTRADICTION_THRESHOLD:
                    contradictions.append((mem1, mem2, similarity))
    
    # 按相似度排序
    contradictions.sort(key=lambda x: x[2], reverse=True)
    
    return contradictions


# ============ 验证 ============
def validate_with_context(mem1: Dict, mem2: Dict) -> Optional[Dict]:
    """
    用当前上下文验证哪个记忆是正确的
    
    简单策略：
    1. 更新时间更近的更可能正确
    2. 权重更高的更可能正确
    3. 类型为 'preference' 的优先级更高
    """
    score1 = 0.0
    score2 = 0.0
    
    # 1. 时间新鲜度（40%）
    if mem1['updated'] > mem2['updated']:
        score1 += 0.4
    else:
        score2 += 0.4
    
    # 2. 权重（30%）
    if mem1['weight'] > mem2['weight']:
        score1 += 0.3
    elif mem2['weight'] > mem1['weight']:
        score2 += 0.3
    
    # 3. 类型优先级（30%）
    type_priority = {'preference': 3, 'skill': 2, 'fact': 1, 'error': 0}
    priority1 = type_priority.get(mem1['type'], 0)
    priority2 = type_priority.get(mem2['type'], 0)
    
    if priority1 > priority2:
        score1 += 0.3
    elif priority2 > priority1:
        score2 += 0.3
    
    # 返回得分更高的
    if score1 > score2:
        return mem1
    elif score2 > score1:
        return mem2
    else:
        return None  # 无法判断


# ============ 解决矛盾 ============
def resolve_contradiction(mem1: Dict, mem2: Dict, auto_resolve: bool = False) -> Dict:
    """解决矛盾"""
    correct = validate_with_context(mem1, mem2)
    
    if not correct:
        return {
            'status': 'undecided',
            'mem1': mem1,
            'mem2': mem2,
            'reason': '无法自动判断，需要人工介入'
        }
    
    incorrect = mem2 if correct == mem1 else mem1
    
    result = {
        'status': 'resolved',
        'correct': correct,
        'incorrect': incorrect,
        'action': 'pending'
    }
    
    if auto_resolve:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 降低错误记忆的权重
        new_weight = max(incorrect['weight'] * 0.5, 0.1)
        cursor.execute("""
            UPDATE memory
            SET weight = ?, updated = ?
            WHERE id = ?
        """, (new_weight, time.time(), incorrect['id']))
        
        # 建立替代关系
        cursor.execute("""
            INSERT INTO memory_relations (memory_id1, memory_id2, relation_type, weight)
            VALUES (?, ?, 'supersedes', 1.0)
        """, (correct['id'], incorrect['id']))
        
        # 记录操作
        cursor.execute("""
            INSERT INTO operations (operation, details)
            VALUES (?, ?)
        """, ('resolve_contradiction', json.dumps({
            'correct_id': correct['id'],
            'incorrect_id': incorrect['id'],
            'old_weight': incorrect['weight'],
            'new_weight': new_weight
        })))
        
        conn.commit()
        conn.close()
        
        result['action'] = 'resolved'
        result['new_weight'] = new_weight
    
    return result


def batch_resolve_contradictions(auto_resolve: bool = False) -> List[Dict]:
    """批量解决矛盾"""
    contradictions = find_contradictions()
    
    results = []
    for mem1, mem2, similarity in contradictions:
        result = resolve_contradiction(mem1, mem2, auto_resolve)
        result['similarity'] = similarity
        results.append(result)
    
    return results


# ============ 统计 ============
def analyze_contradictions() -> Dict:
    """分析矛盾情况"""
    contradictions = find_contradictions()
    
    total = len(contradictions)
    
    # 按类型分类
    by_type = {}
    for mem1, mem2, _ in contradictions:
        key = f"{mem1['type']} vs {mem2['type']}"
        by_type[key] = by_type.get(key, 0) + 1
    
    return {
        'total_contradictions': total,
        'by_type': by_type,
        'top_contradictions': [
            {
                'mem1_id': mem1['id'],
                'mem1_content': mem1['content'][:60] + '...',
                'mem2_id': mem2['id'],
                'mem2_content': mem2['content'][:60] + '...',
                'similarity': similarity
            }
            for mem1, mem2, similarity in contradictions[:10]
        ]
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Adversarial Memory Validation - 对抗性记忆验证')
    parser.add_argument('action', choices=['find', 'resolve', 'analyze'], help='操作类型')
    parser.add_argument('--auto', action='store_true', help='自动解决矛盾')
    parser.add_argument('--limit', type=int, default=20, help='显示数量')
    
    args = parser.parse_args()
    
    if args.action == 'find':
        contradictions = find_contradictions()
        
        print(f"\n🔍 发现 {len(contradictions)} 对潜在矛盾\n")
        
        for i, (mem1, mem2, similarity) in enumerate(contradictions[:args.limit], 1):
            print(f"{i}. 相似度: {similarity:.2f}")
            print(f"   记忆 {mem1['id']}: {mem1['content'][:60]}...")
            print(f"   记忆 {mem2['id']}: {mem2['content'][:60]}...")
            print()
    
    elif args.action == 'resolve':
        results = batch_resolve_contradictions(auto_resolve=args.auto)
        
        if args.auto:
            resolved = [r for r in results if r['status'] == 'resolved']
            undecided = [r for r in results if r['status'] == 'undecided']
            
            print(f"\n✅ 已解决 {len(resolved)} 对矛盾")
            print(f"⚠️  无法判断 {len(undecided)} 对矛盾\n")
            
            for i, result in enumerate(resolved[:10], 1):
                print(f"{i}. 正确: 记忆 {result['correct']['id']}")
                print(f"   错误: 记忆 {result['incorrect']['id']} (权重降至 {result['new_weight']:.2f})")
        else:
            print(f"\n🔍 预览模式：发现 {len(results)} 对矛盾\n")
            
            for i, result in enumerate(results[:args.limit], 1):
                if result['status'] == 'resolved':
                    print(f"{i}. 建议保留: 记忆 {result['correct']['id']}")
                    print(f"   建议降权: 记忆 {result['incorrect']['id']}")
                else:
                    print(f"{i}. 无法判断:")
                    print(f"   记忆 {result['mem1']['id']} vs 记忆 {result['mem2']['id']}")
                print()
            
            print("使用 --auto 执行自动解决")
    
    elif args.action == 'analyze':
        stats = analyze_contradictions()
        
        print(f"\n📊 矛盾分析\n")
        print(f"总矛盾数: {stats['total_contradictions']}")
        
        if stats['by_type']:
            print(f"\n按类型分布:")
            for type_pair, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {type_pair}: {count}")
        
        if stats['top_contradictions']:
            print(f"\nTop 10 矛盾:")
            for i, c in enumerate(stats['top_contradictions'], 1):
                print(f"{i}. [ID:{c['mem1_id']}] {c['mem1_content']}")
                print(f"   vs [ID:{c['mem2_id']}] {c['mem2_content']}")
                print(f"   相似度: {c['similarity']:.2f}")
                print()


if __name__ == '__main__':
    main()
