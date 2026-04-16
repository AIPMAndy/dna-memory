#!/usr/bin/env python3
"""
Memory Quality Evaluator - 记忆质量评估系统
功能：
- 自动评估记忆质量
- 清理低质量记忆
- 识别高价值记忆
- 记忆健康度报告
"""

import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"

# 质量评分权重
WEIGHTS = {
    'access_frequency': 0.25,  # 访问频率
    'freshness': 0.15,         # 新鲜度
    'specificity': 0.20,       # 具体性
    'validation': 0.20,        # 验证状态
    'connections': 0.10,       # 关联度
    'importance': 0.10         # 重要性（权重）
}

# 质量阈值
QUALITY_THRESHOLDS = {
    'excellent': 0.8,
    'good': 0.6,
    'fair': 0.4,
    'poor': 0.2
}


# ============ 质量评分 ============
def calculate_access_frequency_score(memory: Dict) -> float:
    """计算访问频率得分"""
    # 基于更新频率
    created = memory.get('created', time.time())
    updated = memory.get('updated', created)
    age_days = (time.time() - created) / 86400
    
    if age_days < 1:
        age_days = 1  # 避免除零
    
    # 假设每次 recall 都会更新 updated 时间
    # 更新越频繁，得分越高
    update_gap_days = (time.time() - updated) / 86400
    
    if update_gap_days < 1:
        return 1.0
    elif update_gap_days < 7:
        return 0.8
    elif update_gap_days < 30:
        return 0.5
    elif update_gap_days < 90:
        return 0.3
    else:
        return 0.1


def calculate_freshness_score(memory: Dict) -> float:
    """计算新鲜度得分"""
    created = memory.get('created', time.time())
    days_old = (time.time() - created) / 86400
    
    # 新记忆得分高
    if days_old < 7:
        return 1.0
    elif days_old < 30:
        return 0.8
    elif days_old < 90:
        return 0.6
    elif days_old < 180:
        return 0.4
    elif days_old < 365:
        return 0.2
    else:
        return 0.1


def calculate_specificity_score(memory: Dict) -> float:
    """计算具体性得分（越具体越有用）"""
    content = memory.get('content', '')
    
    score = 0.0
    
    # 1. 长度（太短或太长都不好）
    length = len(content)
    if 20 <= length <= 200:
        score += 0.3
    elif 10 <= length < 20 or 200 < length <= 500:
        score += 0.2
    else:
        score += 0.1
    
    # 2. 包含具体信息（数字、时间、名称）
    if any(char.isdigit() for char in content):
        score += 0.2
    
    # 3. 包含动词（表示行动）
    action_words = ['做', '用', '执行', '调用', '运行', '检查', '优化', '修复']
    if any(word in content for word in action_words):
        score += 0.2
    
    # 4. 包含否定（错误教训）
    negative_words = ['不要', '避免', '禁止', '错误', '失败', '问题']
    if any(word in content for word in negative_words):
        score += 0.15
    
    # 5. 包含因果关系
    causal_words = ['因为', '所以', '导致', '原因', '结果']
    if any(word in content for word in causal_words):
        score += 0.15
    
    return min(score, 1.0)


def calculate_validation_score(memory: Dict, conn: sqlite3.Connection) -> float:
    """计算验证状态得分"""
    memory_id = memory.get('id')
    cursor = conn.cursor()
    
    # 检查是否有纠正记录
    cursor.execute("""
        SELECT COUNT(*) FROM operations
        WHERE operation = 'correct' AND details LIKE ?
    """, (f'%{memory_id}%',))
    
    corrections = cursor.fetchone()[0]
    
    if corrections > 0:
        return 0.2  # 被纠正过，质量低
    
    # 检查是否被引用
    cursor.execute("""
        SELECT COUNT(*) FROM memory_relations
        WHERE memory_id1 = ? OR memory_id2 = ?
    """, (memory_id, memory_id))
    
    references = cursor.fetchone()[0]
    
    if references > 5:
        return 1.0
    elif references > 2:
        return 0.8
    elif references > 0:
        return 0.6
    else:
        return 0.4


def calculate_connections_score(memory: Dict, conn: sqlite3.Connection) -> float:
    """计算关联度得分"""
    memory_id = memory.get('id')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM memory_relations
        WHERE memory_id1 = ? OR memory_id2 = ?
    """, (memory_id, memory_id))
    
    connections = cursor.fetchone()[0]
    
    if connections >= 10:
        return 1.0
    elif connections >= 5:
        return 0.8
    elif connections >= 2:
        return 0.6
    elif connections >= 1:
        return 0.4
    else:
        return 0.2


def calculate_importance_score(memory: Dict) -> float:
    """计算重要性得分（基于权重）"""
    weight = memory.get('weight', 0.5)
    return weight


def evaluate_memory_quality(memory: Dict, conn: sqlite3.Connection) -> Dict:
    """综合评估记忆质量"""
    scores = {
        'access_frequency': calculate_access_frequency_score(memory),
        'freshness': calculate_freshness_score(memory),
        'specificity': calculate_specificity_score(memory),
        'validation': calculate_validation_score(memory, conn),
        'connections': calculate_connections_score(memory, conn),
        'importance': calculate_importance_score(memory)
    }
    
    # 加权总分
    total_score = sum(scores[k] * WEIGHTS[k] for k in scores)
    
    # 质量等级
    if total_score >= QUALITY_THRESHOLDS['excellent']:
        grade = 'excellent'
    elif total_score >= QUALITY_THRESHOLDS['good']:
        grade = 'good'
    elif total_score >= QUALITY_THRESHOLDS['fair']:
        grade = 'fair'
    else:
        grade = 'poor'
    
    return {
        'total_score': total_score,
        'grade': grade,
        'scores': scores
    }


# ============ 批量评估 ============
def evaluate_all_memories(min_score: float = 0.0) -> List[Dict]:
    """评估所有记忆"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, content, type, tags, weight, created, updated
        FROM memory
        ORDER BY updated DESC
    """)
    
    results = []
    for row in cursor.fetchall():
        memory = {
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'tags': row[3],
            'weight': row[4],
            'created': row[5],
            'updated': row[6]
        }
        
        quality = evaluate_memory_quality(memory, conn)
        
        if quality['total_score'] >= min_score:
            memory['quality'] = quality
            results.append(memory)
    
    conn.close()
    
    # 按质量排序
    results.sort(key=lambda x: x['quality']['total_score'], reverse=True)
    
    return results


# ============ 清理低质量记忆 ============
def cleanup_low_quality_memories(threshold: float = 0.2, dry_run: bool = True) -> List[int]:
    """清理低质量记忆"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, content, type, tags, weight, created, updated
        FROM memory
    """)
    
    to_delete = []
    for row in cursor.fetchall():
        memory = {
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'tags': row[3],
            'weight': row[4],
            'created': row[5],
            'updated': row[6]
        }
        
        quality = evaluate_memory_quality(memory, conn)
        
        if quality['total_score'] < threshold:
            to_delete.append(memory['id'])
    
    if not dry_run and to_delete:
        # 删除低质量记忆
        cursor.executemany("DELETE FROM memory WHERE id = ?", [(id,) for id in to_delete])
        
        # 记录操作
        cursor.execute("""
            INSERT INTO operations (operation, details)
            VALUES (?, ?)
        """, ('cleanup', json.dumps({'deleted_ids': to_delete, 'threshold': threshold})))
        
        conn.commit()
    
    conn.close()
    
    return to_delete


# ============ 健康度报告 ============
def generate_health_report() -> Dict:
    """生成记忆健康度报告"""
    memories = evaluate_all_memories()
    
    total = len(memories)
    if total == 0:
        return {'error': '没有记忆'}
    
    grades = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
    for memory in memories:
        grade = memory['quality']['grade']
        grades[grade] += 1
    
    avg_score = sum(m['quality']['total_score'] for m in memories) / total
    
    # 识别高价值记忆
    top_memories = memories[:10]
    
    # 识别低质量记忆
    low_quality = [m for m in memories if m['quality']['grade'] == 'poor']
    
    return {
        'total_memories': total,
        'average_score': avg_score,
        'grade_distribution': grades,
        'top_memories': top_memories,
        'low_quality_count': len(low_quality),
        'low_quality_memories': low_quality[:10]
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Memory Quality Evaluator')
    parser.add_argument('action', choices=['evaluate', 'cleanup', 'report'], help='操作类型')
    parser.add_argument('--min-score', type=float, default=0.0, help='最低质量分数')
    parser.add_argument('--threshold', type=float, default=0.2, help='清理阈值')
    parser.add_argument('--dry-run', action='store_true', help='预览模式（不实际删除）')
    parser.add_argument('--limit', type=int, default=20, help='显示数量')
    
    args = parser.parse_args()
    
    if args.action == 'evaluate':
        memories = evaluate_all_memories(min_score=args.min_score)
        print(f"✅ 评估了 {len(memories)} 条记忆\n")
        
        for i, memory in enumerate(memories[:args.limit], 1):
            quality = memory['quality']
            print(f"{i}. [ID:{memory['id']}] [{memory['type']}] 质量:{quality['total_score']:.2f} ({quality['grade']})")
            print(f"   {memory['content'][:80]}...")
            print(f"   详细得分: 访问频率:{quality['scores']['access_frequency']:.2f} "
                  f"新鲜度:{quality['scores']['freshness']:.2f} "
                  f"具体性:{quality['scores']['specificity']:.2f}")
            print()
    
    elif args.action == 'cleanup':
        to_delete = cleanup_low_quality_memories(threshold=args.threshold, dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"🔍 预览模式：将删除 {len(to_delete)} 条低质量记忆")
            print(f"   IDs: {to_delete[:20]}")
            print("\n   使用 --no-dry-run 执行实际删除")
        else:
            print(f"✅ 已删除 {len(to_delete)} 条低质量记忆")
    
    elif args.action == 'report':
        report = generate_health_report()
        
        if 'error' in report:
            print(f"❌ {report['error']}")
            return
        
        print("📊 记忆健康度报告\n")
        print(f"总记忆数: {report['total_memories']}")
        print(f"平均质量: {report['average_score']:.2f}")
        print(f"\n质量分布:")
        print(f"  优秀 (≥0.8): {report['grade_distribution']['excellent']} 条")
        print(f"  良好 (≥0.6): {report['grade_distribution']['good']} 条")
        print(f"  一般 (≥0.4): {report['grade_distribution']['fair']} 条")
        print(f"  较差 (<0.4): {report['grade_distribution']['poor']} 条")
        
        print(f"\n🏆 Top 10 高价值记忆:")
        for i, memory in enumerate(report['top_memories'], 1):
            print(f"{i}. [ID:{memory['id']}] 质量:{memory['quality']['total_score']:.2f}")
            print(f"   {memory['content'][:80]}...")
        
        if report['low_quality_count'] > 0:
            print(f"\n⚠️  发现 {report['low_quality_count']} 条低质量记忆")
            print("   建议运行: python3 memory_quality.py cleanup --threshold 0.2")


if __name__ == '__main__':
    main()
