#!/usr/bin/env python3
"""
Memory Reinforcement - 记忆自我强化学习循环
功能：
- 验证记忆是否真的有用
- 自动强化有用的记忆
- 自动衰减无用的记忆
- 追踪记忆使用效果
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"
REINFORCEMENT_LOG = MEMORY_DIR / "reinforcement.json"

# 强化参数
REINFORCE_DELTA = 0.1  # 有用时增加的权重
DECAY_DELTA = 0.05     # 无用时减少的权重
MAX_WEIGHT = 1.0
MIN_WEIGHT = 0.1


# ============ 记忆使用追踪 ============
def track_memory_usage(memory_ids: List[int], task_id: str, success: bool, feedback: Optional[str] = None):
    """追踪记忆使用情况"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 记录使用日志
    for memory_id in memory_ids:
        cursor.execute("""
            INSERT INTO operations (operation, details)
            VALUES (?, ?)
        """, ('memory_usage', json.dumps({
            'memory_id': memory_id,
            'task_id': task_id,
            'success': success,
            'feedback': feedback,
            'timestamp': time.time()
        })))
    
    conn.commit()
    conn.close()


def reinforce_memory(memory_id: int, delta: float = REINFORCE_DELTA, reason: str = "useful"):
    """强化记忆（增加权重）"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取当前权重
    cursor.execute("SELECT weight FROM memory WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    current_weight = row[0]
    new_weight = min(current_weight + delta, MAX_WEIGHT)
    
    # 更新权重
    cursor.execute("""
        UPDATE memory
        SET weight = ?, updated = ?
        WHERE id = ?
    """, (new_weight, time.time(), memory_id))
    
    # 记录强化操作
    cursor.execute("""
        INSERT INTO operations (operation, details)
        VALUES (?, ?)
    """, ('reinforce', json.dumps({
        'memory_id': memory_id,
        'old_weight': current_weight,
        'new_weight': new_weight,
        'delta': delta,
        'reason': reason
    })))
    
    conn.commit()
    conn.close()
    
    return True


def decay_memory(memory_id: int, delta: float = DECAY_DELTA, reason: str = "not_useful"):
    """衰减记忆（减少权重）"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取当前权重
    cursor.execute("SELECT weight FROM memory WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    current_weight = row[0]
    new_weight = max(current_weight - delta, MIN_WEIGHT)
    
    # 更新权重
    cursor.execute("""
        UPDATE memory
        SET weight = ?, updated = ?
        WHERE id = ?
    """, (new_weight, time.time(), memory_id))
    
    # 记录衰减操作
    cursor.execute("""
        INSERT INTO operations (operation, details)
        VALUES (?, ?)
    """, ('decay', json.dumps({
        'memory_id': memory_id,
        'old_weight': current_weight,
        'new_weight': new_weight,
        'delta': delta,
        'reason': reason
    })))
    
    conn.commit()
    conn.close()
    
    return True


# ============ 批量强化/衰减 ============
def batch_reinforce(memory_ids: List[int], task_result: Dict):
    """批量强化记忆"""
    success_count = 0
    
    for memory_id in memory_ids:
        if reinforce_memory(memory_id, reason=f"task_success: {task_result.get('task_id')}"):
            success_count += 1
    
    return success_count


def batch_decay(memory_ids: List[int], task_result: Dict):
    """批量衰减记忆"""
    decay_count = 0
    
    for memory_id in memory_ids:
        if decay_memory(memory_id, reason=f"task_failed: {task_result.get('task_id')}"):
            decay_count += 1
    
    return decay_count


# ============ 强化学习循环 ============
def reinforcement_loop(query: str, task_id: str, success: bool, used_memory_ids: Optional[List[int]] = None):
    """
    完整的强化学习循环
    
    Args:
        query: 查询关键词
        task_id: 任务 ID
        success: 任务是否成功
        used_memory_ids: 实际使用的记忆 ID（如果为 None，则自动 recall）
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 如果没有提供使用的记忆 ID，自动 recall
    if used_memory_ids is None:
        # 简单的 recall（可以替换为 advanced_recall）
        cursor.execute("""
            SELECT id FROM memory
            WHERE content LIKE ?
            ORDER BY weight DESC
            LIMIT 10
        """, (f'%{query}%',))
        
        used_memory_ids = [row[0] for row in cursor.fetchall()]
    
    # 追踪使用
    track_memory_usage(used_memory_ids, task_id, success)
    
    # 根据结果强化或衰减
    if success:
        reinforced = batch_reinforce(used_memory_ids, {'task_id': task_id})
        result = f"✅ 强化了 {reinforced} 条记忆"
    else:
        decayed = batch_decay(used_memory_ids, {'task_id': task_id})
        result = f"⚠️  衰减了 {decayed} 条记忆"
    
    conn.close()
    
    return {
        'query': query,
        'task_id': task_id,
        'success': success,
        'memory_count': len(used_memory_ids),
        'result': result
    }


# ============ 统计分析 ============
def analyze_reinforcement_history(days: int = 7) -> Dict:
    """分析强化历史"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cutoff = time.time() - (days * 86400)
    
    # 统计强化操作
    cursor.execute("""
        SELECT operation, details FROM operations
        WHERE operation IN ('reinforce', 'decay', 'memory_usage')
        AND timestamp > ?
        ORDER BY timestamp DESC
    """, (cutoff,))
    
    reinforce_count = 0
    decay_count = 0
    usage_success = 0
    usage_failed = 0
    
    for row in cursor.fetchall():
        operation = row[0]
        details = json.loads(row[1])
        
        if operation == 'reinforce':
            reinforce_count += 1
        elif operation == 'decay':
            decay_count += 1
        elif operation == 'memory_usage':
            if details.get('success'):
                usage_success += 1
            else:
                usage_failed += 1
    
    conn.close()
    
    total_usage = usage_success + usage_failed
    success_rate = usage_success / total_usage if total_usage > 0 else 0
    
    return {
        'days': days,
        'reinforce_count': reinforce_count,
        'decay_count': decay_count,
        'usage_success': usage_success,
        'usage_failed': usage_failed,
        'success_rate': success_rate
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Memory Reinforcement - 记忆强化学习')
    parser.add_argument('action', choices=['reinforce', 'decay', 'loop', 'analyze'], help='操作类型')
    parser.add_argument('--id', type=int, help='记忆 ID')
    parser.add_argument('--ids', type=int, nargs='+', help='多个记忆 ID')
    parser.add_argument('--query', help='查询关键词（用于 loop）')
    parser.add_argument('--task-id', help='任务 ID（用于 loop）')
    parser.add_argument('--success', action='store_true', help='任务是否成功')
    parser.add_argument('--delta', type=float, help='权重变化量')
    parser.add_argument('--reason', help='原因')
    parser.add_argument('--days', type=int, default=7, help='分析天数')
    
    args = parser.parse_args()
    
    if args.action == 'reinforce':
        if not args.id:
            print("❌ 需要指定 --id")
            return
        
        delta = args.delta or REINFORCE_DELTA
        reason = args.reason or "manual"
        
        if reinforce_memory(args.id, delta, reason):
            print(f"✅ 强化记忆 {args.id}，权重 +{delta}")
        else:
            print(f"❌ 记忆 {args.id} 不存在")
    
    elif args.action == 'decay':
        if not args.id:
            print("❌ 需要指定 --id")
            return
        
        delta = args.delta or DECAY_DELTA
        reason = args.reason or "manual"
        
        if decay_memory(args.id, delta, reason):
            print(f"⚠️  衰减记忆 {args.id}，权重 -{delta}")
        else:
            print(f"❌ 记忆 {args.id} 不存在")
    
    elif args.action == 'loop':
        if not args.query or not args.task_id:
            print("❌ 需要指定 --query 和 --task-id")
            return
        
        result = reinforcement_loop(
            query=args.query,
            task_id=args.task_id,
            success=args.success,
            used_memory_ids=args.ids
        )
        
        print(f"\n📊 强化学习循环结果：")
        print(f"   查询: {result['query']}")
        print(f"   任务: {result['task_id']}")
        print(f"   成功: {result['success']}")
        print(f"   使用记忆数: {result['memory_count']}")
        print(f"   {result['result']}")
    
    elif args.action == 'analyze':
        stats = analyze_reinforcement_history(days=args.days)
        
        print(f"\n📊 强化学习统计（最近 {stats['days']} 天）\n")
        print(f"强化次数: {stats['reinforce_count']}")
        print(f"衰减次数: {stats['decay_count']}")
        print(f"成功使用: {stats['usage_success']}")
        print(f"失败使用: {stats['usage_failed']}")
        print(f"成功率: {stats['success_rate']:.1%}")


if __name__ == '__main__':
    main()
