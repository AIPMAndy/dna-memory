#!/usr/bin/env python3
"""
Meta Memory - 元记忆系统
功能：
- 追踪记忆系统本身的演化
- 记录质量趋势
- 监控系统健康度
- 触发自我修复
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
META_MEMORY_FILE = MEMORY_DIR / "meta_memory.json"

# 健康阈值
QUALITY_DECLINE_THRESHOLD = 3  # 连续下降次数
MIN_HEALTHY_QUALITY = 0.6      # 最低健康质量


# ============ 元记忆结构 ============
def load_meta_memory() -> Dict:
    """加载元记忆"""
    if META_MEMORY_FILE.exists():
        with open(META_MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 初始化
    return {
        'created_at': time.time(),
        'total_memories': 0,
        'quality_trend': [],
        'recall_accuracy': 0.0,
        'false_positive_rate': 0.0,
        'distillation_count': 0,
        'reinforcement_cycles': 0,
        'evolution_milestones': [],
        'health_checks': []
    }


def save_meta_memory(meta: Dict):
    """保存元记忆"""
    with open(META_MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


# ============ 质量追踪 ============
def calculate_current_quality() -> float:
    """计算当前记忆系统质量"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取所有记忆的平均权重
    cursor.execute("SELECT AVG(weight) FROM memory")
    avg_weight = cursor.fetchone()[0] or 0.5
    
    # 获取长期记忆比例
    cursor.execute("SELECT COUNT(*) FROM memory WHERE long_term = 1")
    long_term_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory")
    total_count = cursor.fetchone()[0]
    
    long_term_ratio = long_term_count / total_count if total_count > 0 else 0
    
    conn.close()
    
    # 综合质量 = 平均权重 * 0.7 + 长期记忆比例 * 0.3
    quality = avg_weight * 0.7 + long_term_ratio * 0.3
    
    return quality


def update_quality_trend():
    """更新质量趋势"""
    meta = load_meta_memory()
    
    current_quality = calculate_current_quality()
    
    meta['quality_trend'].append({
        'timestamp': time.time(),
        'quality': current_quality
    })
    
    # 只保留最近 30 天
    cutoff = time.time() - (30 * 86400)
    meta['quality_trend'] = [
        q for q in meta['quality_trend']
        if q['timestamp'] > cutoff
    ]
    
    save_meta_memory(meta)
    
    return current_quality


# ============ 健康检查 ============
def is_quality_declining(trend: List[Dict], window: int = 5) -> bool:
    """检测质量是否持续下降"""
    if len(trend) < window:
        return False
    
    recent = trend[-window:]
    
    # 检查是否连续下降
    declining = True
    for i in range(1, len(recent)):
        if recent[i]['quality'] >= recent[i-1]['quality']:
            declining = False
            break
    
    return declining


def health_check() -> Dict:
    """健康检查"""
    meta = load_meta_memory()
    
    # 更新质量趋势
    current_quality = update_quality_trend()
    
    # 检查质量下降
    declining = is_quality_declining(meta['quality_trend'])
    
    # 检查是否低于健康阈值
    unhealthy = current_quality < MIN_HEALTHY_QUALITY
    
    # 统计记忆数量
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM memory")
    total_memories = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE weight < 0.3")
    low_quality_count = cursor.fetchone()[0]
    
    conn.close()
    
    # 健康状态
    status = 'healthy'
    issues = []
    
    if declining:
        status = 'warning'
        issues.append('质量持续下降')
    
    if unhealthy:
        status = 'critical'
        issues.append(f'质量低于健康阈值 ({current_quality:.2f} < {MIN_HEALTHY_QUALITY})')
    
    if low_quality_count > total_memories * 0.3:
        status = 'warning'
        issues.append(f'低质量记忆过多 ({low_quality_count}/{total_memories})')
    
    health_result = {
        'timestamp': time.time(),
        'status': status,
        'current_quality': current_quality,
        'total_memories': total_memories,
        'low_quality_count': low_quality_count,
        'issues': issues
    }
    
    # 记录健康检查
    meta['health_checks'].append(health_result)
    
    # 只保留最近 30 次
    meta['health_checks'] = meta['health_checks'][-30:]
    
    save_meta_memory(meta)
    
    return health_result


# ============ 自我修复 ============
def trigger_self_repair():
    """触发自我修复"""
    print("🔧 触发自我修复...")
    
    repairs = []
    
    # 1. 清理低质量记忆
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM memory WHERE weight < 0.2")
    low_quality = cursor.fetchone()[0]
    
    if low_quality > 0:
        cursor.execute("DELETE FROM memory WHERE weight < 0.2")
        conn.commit()
        repairs.append(f"清理了 {low_quality} 条低质量记忆")
    
    # 2. 触发 reflect
    cursor.execute("""
        SELECT COUNT(*) FROM memory
        WHERE short_term = 1 AND weight > 0.7
    """)
    high_quality_short_term = cursor.fetchone()[0]
    
    if high_quality_short_term > 0:
        cursor.execute("""
            UPDATE memory
            SET long_term = 1, short_term = 0
            WHERE short_term = 1 AND weight > 0.7
        """)
        conn.commit()
        repairs.append(f"晋升了 {high_quality_short_term} 条高质量记忆到长期记忆")
    
    # 3. 记录修复操作
    cursor.execute("""
        INSERT INTO operations (operation, details)
        VALUES (?, ?)
    """, ('self_repair', json.dumps({
        'repairs': repairs,
        'timestamp': time.time()
    })))
    
    conn.commit()
    conn.close()
    
    # 4. 更新元记忆
    meta = load_meta_memory()
    meta['evolution_milestones'].append({
        'timestamp': time.time(),
        'event': 'self_repair',
        'details': repairs
    })
    save_meta_memory(meta)
    
    return repairs


# ============ 演化里程碑 ============
def add_milestone(event: str, details: Optional[str] = None):
    """添加演化里程碑"""
    meta = load_meta_memory()
    
    meta['evolution_milestones'].append({
        'timestamp': time.time(),
        'event': event,
        'details': details
    })
    
    save_meta_memory(meta)


# ============ 统计报告 ============
def generate_evolution_report() -> Dict:
    """生成演化报告"""
    meta = load_meta_memory()
    
    # 计算系统年龄
    age_days = (time.time() - meta['created_at']) / 86400
    
    # 质量趋势分析
    if len(meta['quality_trend']) >= 2:
        first_quality = meta['quality_trend'][0]['quality']
        last_quality = meta['quality_trend'][-1]['quality']
        quality_change = last_quality - first_quality
    else:
        quality_change = 0
    
    # 健康状态统计
    health_statuses = [h['status'] for h in meta['health_checks']]
    healthy_count = health_statuses.count('healthy')
    warning_count = health_statuses.count('warning')
    critical_count = health_statuses.count('critical')
    
    return {
        'age_days': age_days,
        'total_memories': meta['total_memories'],
        'quality_trend_length': len(meta['quality_trend']),
        'quality_change': quality_change,
        'distillation_count': meta['distillation_count'],
        'reinforcement_cycles': meta['reinforcement_cycles'],
        'milestones_count': len(meta['evolution_milestones']),
        'health_checks': {
            'total': len(meta['health_checks']),
            'healthy': healthy_count,
            'warning': warning_count,
            'critical': critical_count
        },
        'recent_milestones': meta['evolution_milestones'][-5:]
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Meta Memory - 元记忆系统')
    parser.add_argument('action', choices=['check', 'repair', 'report', 'milestone'], help='操作类型')
    parser.add_argument('--event', help='里程碑事件名称')
    parser.add_argument('--details', help='里程碑详情')
    
    args = parser.parse_args()
    
    if args.action == 'check':
        result = health_check()
        
        print(f"\n🏥 健康检查结果\n")
        print(f"状态: {result['status'].upper()}")
        print(f"当前质量: {result['current_quality']:.2f}")
        print(f"总记忆数: {result['total_memories']}")
        print(f"低质量记忆: {result['low_quality_count']}")
        
        if result['issues']:
            print(f"\n⚠️  发现问题:")
            for issue in result['issues']:
                print(f"  - {issue}")
            
            if result['status'] == 'critical':
                print("\n建议运行: python3 meta_memory.py repair")
    
    elif args.action == 'repair':
        repairs = trigger_self_repair()
        
        print(f"\n✅ 自我修复完成\n")
        for repair in repairs:
            print(f"  - {repair}")
    
    elif args.action == 'report':
        report = generate_evolution_report()
        
        print(f"\n📊 演化报告\n")
        print(f"系统年龄: {report['age_days']:.1f} 天")
        print(f"总记忆数: {report['total_memories']}")
        print(f"质量趋势记录: {report['quality_trend_length']} 条")
        print(f"质量变化: {report['quality_change']:+.2f}")
        print(f"蒸馏次数: {report['distillation_count']}")
        print(f"强化循环: {report['reinforcement_cycles']}")
        print(f"演化里程碑: {report['milestones_count']}")
        
        print(f"\n健康检查统计:")
        print(f"  健康: {report['health_checks']['healthy']}")
        print(f"  警告: {report['health_checks']['warning']}")
        print(f"  严重: {report['health_checks']['critical']}")
        
        if report['recent_milestones']:
            print(f"\n最近里程碑:")
            for milestone in report['recent_milestones']:
                date = datetime.fromtimestamp(milestone['timestamp']).strftime('%Y-%m-%d %H:%M')
                print(f"  [{date}] {milestone['event']}")
                if milestone.get('details'):
                    print(f"    {milestone['details']}")
    
    elif args.action == 'milestone':
        if not args.event:
            print("❌ 需要指定 --event")
            return
        
        add_milestone(args.event, args.details)
        print(f"✅ 已添加里程碑: {args.event}")


if __name__ == '__main__':
    main()
