#!/usr/bin/env python3
"""
轻量级记忆升华 - 低成本的记忆强化和整合
不调用 LLM，纯算法实现
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from path_utils import get_db_path, get_config_path


class LightweightReflection:
    def __init__(self):
        self.db_path = get_db_path()
        self.config = self._load_config()
        self.conn = None

    def _load_config(self):
        """加载配置"""
        config_path = get_config_path()
        default_config = {
            'reflection': {
                'enabled': True,
                'interval_hours': 24,          # 升华频率（小时）
                'min_memories_for_reflection': 5,  # 最少记忆数触发升华
                'weight_boost_per_recall': 0.05,   # 每次调用增加权重
                'weight_decay_per_day': 0.01,      # 每天衰减权重
                'similar_merge_threshold': 0.7,    # 相似度阈值
            }
        }

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                if 'reflection' in user_config:
                    default_config['reflection'].update(user_config['reflection'])

        return default_config['reflection']

    def connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    def should_run_reflection(self) -> bool:
        """检查是否需要运行升华"""
        if not self.config['enabled']:
            return False

        cursor = self.conn.cursor()

        # 检查记忆数量
        cursor.execute("SELECT COUNT(*) FROM memory")
        total = cursor.fetchone()[0]

        if total < self.config['min_memories_for_reflection']:
            return False

        # 检查上次升华时间
        cursor.execute("""
            SELECT MAX(timestamp) FROM operations
            WHERE operation = 'reflection'
        """)
        last_reflection = cursor.fetchone()[0]

        if last_reflection:
            last_time = datetime.fromtimestamp(last_reflection)
            if datetime.now() - last_time < timedelta(hours=self.config['interval_hours']):
                return False

        return True

    def boost_frequently_accessed(self):
        """提升频繁访问的记忆权重"""
        cursor = self.conn.cursor()

        # 找到最近被访问的记忆
        cursor.execute("""
            SELECT id, recall_count, weight
            FROM memory
            WHERE recall_count > 0 AND weight < 1.0
            ORDER BY recall_count DESC
            LIMIT 20
        """)

        boosted_count = 0
        for row in cursor.fetchall():
            new_weight = min(
                1.0,
                row['weight'] + (row['recall_count'] * self.config['weight_boost_per_recall'])
            )

            cursor.execute("""
                UPDATE memory SET weight = ? WHERE id = ?
            """, (new_weight, row['id']))

            boosted_count += 1

        self.conn.commit()
        return boosted_count

    def decay_old_memories(self):
        """衰减长期未访问的记忆"""
        cursor = self.conn.cursor()

        # 找到超过 7 天未访问的记忆
        seven_days_ago = datetime.now().timestamp() - (7 * 24 * 3600)

        cursor.execute("""
            SELECT id, weight, last_accessed
            FROM memory
            WHERE last_accessed < ? AND weight > 0.1
        """, (seven_days_ago,))

        decayed_count = 0
        for row in cursor.fetchall():
            days_inactive = (datetime.now().timestamp() - row['last_accessed']) / (24 * 3600)
            decay = days_inactive * self.config['weight_decay_per_day']

            new_weight = max(0.1, row['weight'] - decay)

            cursor.execute("""
                UPDATE memory SET weight = ? WHERE id = ?
            """, (new_weight, row['id']))

            decayed_count += 1

        self.conn.commit()
        return decayed_count

    def promote_to_long_term(self):
        """将高权重记忆提升为长期记忆"""
        cursor = self.conn.cursor()

        # 权重 >= 0.8 且访问次数 >= 3 的记忆
        cursor.execute("""
            UPDATE memory
            SET long_term = 1
            WHERE weight >= 0.8 AND recall_count >= 3 AND long_term = 0
        """)

        promoted_count = cursor.rowcount
        self.conn.commit()
        return promoted_count

    def find_similar_memories(self):
        """找到相似的记忆（简单的关键词重叠）"""
        cursor = self.conn.cursor()

        # 获取所有记忆
        cursor.execute("SELECT id, content FROM memory WHERE short_term = 1")
        memories = cursor.fetchall()

        similar_groups = []

        for i, mem1 in enumerate(memories):
            for mem2 in memories[i+1:]:
                # 简单的关键词重叠检测
                words1 = set(mem1['content'].split())
                words2 = set(mem2['content'].split())

                if len(words1) == 0 or len(words2) == 0:
                    continue

                overlap = len(words1 & words2)
                similarity = overlap / min(len(words1), len(words2))

                if similarity >= self.config['similar_merge_threshold']:
                    similar_groups.append((mem1['id'], mem2['id'], similarity))

        return similar_groups

    def log_reflection(self, details: dict):
        """记录升华操作"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO operations (operation, timestamp, details)
            VALUES ('reflection', ?, ?)
        """, (datetime.now().timestamp(), json.dumps(details, ensure_ascii=False)))

        self.conn.commit()

    def run_reflection(self) -> dict:
        """执行完整的升华流程"""
        if not self.should_run_reflection():
            return {'skipped': True, 'reason': 'Not yet due'}

        results = {}

        # 1. 提升频繁访问的记忆
        results['boosted'] = self.boost_frequently_accessed()

        # 2. 衰减旧记忆
        results['decayed'] = self.decay_old_memories()

        # 3. 提升到长期记忆
        results['promoted'] = self.promote_to_long_term()

        # 4. 找到相似记忆（仅报告，不自动合并）
        results['similar_found'] = len(self.find_similar_memories())

        # 记录操作
        self.log_reflection(results)

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='轻量级记忆升华')
    parser.add_argument('action', choices=['run', 'status', 'config'],
                       default='status', nargs='?',
                       help='操作: run=执行升华, status=查看状态, config=配置')
    parser.add_argument('--force', action='store_true', help='强制执行（忽略时间间隔）')

    args = parser.parse_args()

    reflection = LightweightReflection()
    reflection.connect()

    try:
        if args.action == 'status':
            cursor = reflection.conn.cursor()

            # 获取上次升华时间
            cursor.execute("""
                SELECT timestamp, details FROM operations
                WHERE operation = 'reflection'
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            last = cursor.fetchone()

            print("📊 记忆升华状态")
            print("=" * 60)
            print(f"升华功能: {'启用' if reflection.config['enabled'] else '禁用'}")
            print(f"升华频率: 每 {reflection.config['interval_hours']} 小时")
            print(f"最少记忆数: {reflection.config['min_memories_for_reflection']}")

            if last:
                last_time = datetime.fromtimestamp(last['timestamp'])
                print(f"\n上次升华: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")

                try:
                    details = json.loads(last['details'])
                    print(f"  - 提升: {details.get('boosted', 0)} 条")
                    print(f"  - 衰减: {details.get('decayed', 0)} 条")
                    print(f"  - 提升到长期: {details.get('promoted', 0)} 条")
                    print(f"  - 发现相似: {details.get('similar_found', 0)} 组")
                except:
                    pass

                next_time = last_time + timedelta(hours=reflection.config['interval_hours'])
                if next_time > datetime.now():
                    print(f"\n下次升华: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  ({(next_time - datetime.now()).total_seconds() / 3600:.1f} 小时后)")
                else:
                    print(f"\n下次升华: 可以立即执行")
            else:
                print(f"\n尚未执行过升华")

        elif args.action == 'run':
            if args.force:
                reflection.config['enabled'] = True
                reflection.config['min_memories_for_reflection'] = 0

            if not reflection.should_run_reflection() and not args.force:
                print("⏭️  升华暂不需要执行")
                print("   原因: 时间间隔未到或记忆数量不足")
                print("   使用 --force 强制执行")
                return

            print("🔄 执行记忆升华...")
            results = reflection.run_reflection()

            if results.get('skipped'):
                print(f"⏭️  跳过: {results['reason']}")
            else:
                print("✅ 升华完成")
                print(f"  - 提升权重: {results['boosted']} 条")
                print(f"  - 权重衰减: {results['decayed']} 条")
                print(f"  - 提升到长期: {results['promoted']} 条")
                print(f"  - 发现相似: {results['similar_found']} 组")

        elif args.action == 'config':
            print("⚙️  升华配置")
            print("=" * 60)
            for key, value in reflection.config.items():
                print(f"{key}: {value}")
            print(f"\n配置文件: {get_config_path()}")

    finally:
        reflection.close()


if __name__ == '__main__':
    main()
