#!/usr/bin/env python3
"""
进化策略 - 动态调整记忆管理策略
整合自 Evolver 的进化策略预设机制
"""

import os
import random
import time
from typing import Dict, Any


class EvolutionStrategy:
    """记忆进化策略"""
    
    # 策略预设（参考 Evolver）
    STRATEGIES = {
        'balanced': {
            'name': '平衡模式',
            'description': '日常运行，稳步成长',
            'new_memory_weight': 0.5,
            'reinforce_weight': 0.3,
            'decay_weight': 0.2,
            'confidence_threshold': 0.7,
            'reflect_trigger': 20,
        },
        'aggressive': {
            'name': '激进模式',
            'description': '快速学习，大量记录',
            'new_memory_weight': 0.8,
            'reinforce_weight': 0.15,
            'decay_weight': 0.05,
            'confidence_threshold': 0.6,
            'reflect_trigger': 30,
        },
        'conservative': {
            'name': '保守模式',
            'description': '聚焦稳固，减少新增',
            'new_memory_weight': 0.2,
            'reinforce_weight': 0.4,
            'decay_weight': 0.4,
            'confidence_threshold': 0.85,
            'reflect_trigger': 15,
        },
        'cleanup': {
            'name': '清理模式',
            'description': '紧急清理，释放空间',
            'new_memory_weight': 0.0,
            'reinforce_weight': 0.2,
            'decay_weight': 0.8,
            'confidence_threshold': 0.95,
            'reflect_trigger': 10,
        },
    }
    
    def __init__(self, strategy: str = None):
        """
        初始化进化策略
        
        Args:
            strategy: 策略名称（balanced/aggressive/conservative/cleanup）
                     如果为 None，从环境变量 DNA_MEMORY_STRATEGY 读取
        """
        strategy_name = strategy or os.getenv('DNA_MEMORY_STRATEGY', 'balanced')
        
        if strategy_name not in self.STRATEGIES:
            print(f"⚠️  未知策略 '{strategy_name}'，使用默认策略 'balanced'")
            strategy_name = 'balanced'
        
        self.strategy_name = strategy_name
        self.strategy = self.STRATEGIES[strategy_name]
        
        print(f"🧬 进化策略: {self.strategy['name']} - {self.strategy['description']}")
    
    def should_remember(self, signal: Dict[str, Any]) -> bool:
        """
        根据策略决定是否记录
        
        Args:
            signal: 信号字典（包含 confidence）
        
        Returns:
            是否应该记录
        """
        return signal['confidence'] >= self.strategy['confidence_threshold']
    
    def should_reinforce(self, memory: Dict[str, Any]) -> bool:
        """
        根据策略决定是否强化
        
        Args:
            memory: 记忆字典（包含 access_count, weight）
        
        Returns:
            是否应该强化
        """
        # 高频访问 + 策略权重
        access_count = memory.get('access_count', 0)
        current_weight = memory.get('weight', 0.5)
        
        # 已经很高权重的不再强化
        if current_weight >= 0.95:
            return False
        
        # 访问次数达标 + 随机概率
        return (
            access_count >= 3 and
            random.random() < self.strategy['reinforce_weight']
        )
    
    def should_decay(self, memory: Dict[str, Any]) -> bool:
        """
        根据策略决定是否衰减
        
        Args:
            memory: 记忆字典（包含 last_accessed, weight）
        
        Returns:
            是否应该衰减
        """
        last_accessed = memory.get('last_accessed', time.time())
        current_weight = memory.get('weight', 0.5)
        
        # 已经很低权重的不再衰减
        if current_weight <= 0.1:
            return False
        
        # 长期未访问 + 策略权重
        days_since_access = (time.time() - last_accessed) / 86400
        
        return (
            days_since_access > 7 and
            random.random() < self.strategy['decay_weight']
        )
    
    def should_reflect(self, short_term_count: int) -> bool:
        """
        根据策略决定是否触发反思
        
        Args:
            short_term_count: 短期记忆数量
        
        Returns:
            是否应该反思
        """
        return short_term_count >= self.strategy['reflect_trigger']
    
    def calculate_new_weight(
        self,
        current_weight: float,
        action: str,
        reason: str = None
    ) -> float:
        """
        计算新权重
        
        Args:
            current_weight: 当前权重
            action: 动作（reinforce/decay）
            reason: 原因（可选）
        
        Returns:
            新权重
        """
        if action == 'reinforce':
            # 强化：+0.1 到 +0.2
            delta = 0.1 + (self.strategy['reinforce_weight'] * 0.1)
            new_weight = min(current_weight + delta, 1.0)
        
        elif action == 'decay':
            # 衰减：-0.05 到 -0.15
            delta = 0.05 + (self.strategy['decay_weight'] * 0.1)
            new_weight = max(current_weight - delta, 0.0)
        
        else:
            new_weight = current_weight
        
        return round(new_weight, 2)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取当前策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': self.strategy_name,
            'display_name': self.strategy['name'],
            'description': self.strategy['description'],
            'config': {
                'new_memory_weight': self.strategy['new_memory_weight'],
                'reinforce_weight': self.strategy['reinforce_weight'],
                'decay_weight': self.strategy['decay_weight'],
                'confidence_threshold': self.strategy['confidence_threshold'],
                'reflect_trigger': self.strategy['reflect_trigger'],
            }
        }
    
    @classmethod
    def list_strategies(cls) -> None:
        """列出所有可用策略"""
        print("📋 可用进化策略:\n")
        
        for name, config in cls.STRATEGIES.items():
            print(f"  {name}")
            print(f"    名称: {config['name']}")
            print(f"    描述: {config['description']}")
            print(f"    新增权重: {config['new_memory_weight']:.0%}")
            print(f"    强化权重: {config['reinforce_weight']:.0%}")
            print(f"    衰减权重: {config['decay_weight']:.0%}")
            print(f"    置信度阈值: {config['confidence_threshold']:.0%}")
            print(f"    反思触发: {config['reflect_trigger']} 条")
            print()


# ============ CLI ============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='进化策略管理')
    parser.add_argument('--list', action='store_true', help='列出所有策略')
    parser.add_argument('--strategy', help='指定策略')
    parser.add_argument('--info', action='store_true', help='显示当前策略信息')
    parser.add_argument('--test', action='store_true', help='运行测试')
    
    args = parser.parse_args()
    
    if args.list:
        EvolutionStrategy.list_strategies()
    
    elif args.info:
        strategy = EvolutionStrategy(args.strategy)
        info = strategy.get_strategy_info()
        
        print(f"📊 当前策略: {info['display_name']}")
        print(f"   描述: {info['description']}")
        print(f"\n   配置:")
        for key, value in info['config'].items():
            if isinstance(value, float):
                print(f"     {key}: {value:.0%}")
            else:
                print(f"     {key}: {value}")
    
    elif args.test:
        print("🧪 测试进化策略\n")
        
        # 测试不同策略
        for strategy_name in ['balanced', 'aggressive', 'conservative', 'cleanup']:
            print(f"--- {strategy_name.upper()} ---")
            strategy = EvolutionStrategy(strategy_name)
            
            # 测试信号
            test_signal = {'confidence': 0.75}
            print(f"  信号置信度 0.75 → 是否记录: {strategy.should_remember(test_signal)}")
            
            # 测试强化
            test_memory = {'access_count': 5, 'weight': 0.6}
            print(f"  访问5次/权重0.6 → 是否强化: {strategy.should_reinforce(test_memory)}")
            
            # 测试衰减
            test_memory = {'last_accessed': time.time() - 10 * 86400, 'weight': 0.5}
            print(f"  10天未访问/权重0.5 → 是否衰减: {strategy.should_decay(test_memory)}")
            
            # 测试反思
            print(f"  短期记忆25条 → 是否反思: {strategy.should_reflect(25)}")
            
            print()
    
    else:
        parser.print_help()
