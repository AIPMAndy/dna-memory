#!/usr/bin/env python3
"""
会话级记忆（SessionMemory）
用于存储会话期间的临时上下文，减少长期记忆污染
"""

import json
from datetime import datetime
from pathlib import Path

class SessionMemory:
    """会话级记忆（临时上下文）"""
    
    def __init__(self, session_id, storage_path=None):
        self.session_id = session_id
        self.storage_path = storage_path or Path('~/.openclaw/skills/dna-memory/memory/working.json').expanduser()
        
        self.memory = {
            'session_id': session_id,
            'created': datetime.now().isoformat(),
            'task_state': {},      # 当前任务状态
            'temp_decisions': [],  # 临时决策
            'intermediate': [],    # 中间结果
            'context': [],         # 上下文
        }
        
        # 尝试加载已有会话
        self._load()
    
    def _load(self):
        """加载已有会话记忆"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('session_id') == self.session_id:
                        self.memory = data
            except Exception as e:
                print(f"⚠️ 加载会话记忆失败: {e}")
    
    def _save(self):
        """保存会话记忆"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存会话记忆失败: {e}")
    
    def add_task_state(self, key, value):
        """添加任务状态"""
        self.memory['task_state'][key] = value
        self._save()
    
    def get_task_state(self, key, default=None):
        """获取任务状态"""
        return self.memory['task_state'].get(key, default)
    
    def add_decision(self, decision):
        """添加临时决策"""
        self.memory['temp_decisions'].append({
            'content': decision,
            'timestamp': datetime.now().isoformat(),
        })
        self._save()
    
    def add_intermediate(self, result):
        """添加中间结果"""
        self.memory['intermediate'].append({
            'content': result,
            'timestamp': datetime.now().isoformat(),
        })
        self._save()
    
    def add_context(self, context):
        """添加上下文"""
        self.memory['context'].append({
            'content': context,
            'timestamp': datetime.now().isoformat(),
        })
        self._save()
    
    def compress(self, max_items=10):
        """压缩上下文
        
        保留：任务状态、重要决策
        压缩：重复对话、已完成步骤
        丢弃：临时中间结果
        """
        compressed = {
            'session_id': self.session_id,
            'created': self.memory['created'],
            'task_state': self.memory['task_state'],
            'temp_decisions': self.memory['temp_decisions'][-max_items:],  # 只保留最近 N 条
            'context': self.memory['context'][-max_items:],  # 只保留最近 N 条
            'intermediate': [],  # 丢弃中间结果
        }
        
        self.memory = compressed
        self._save()
        
        return compressed
    
    def extract_valuable(self):
        """提取有价值的记忆（会话结束时）
        
        Returns:
            有价值的记忆列表，格式：[{'content': '...', 'type': '...', 'confidence': 0.8}]
        """
        valuable = []
        
        # 从临时决策中提取重要决策
        for decision in self.memory['temp_decisions']:
            if self._is_important(decision['content']):
                valuable.append({
                    'content': decision['content'],
                    'type': 'fact',
                    'confidence': 0.8,
                    'source': 'session_decision',
                })
        
        # 从上下文中提取重要信息
        for ctx in self.memory['context']:
            if self._is_important(ctx['content']):
                valuable.append({
                    'content': ctx['content'],
                    'type': 'fact',
                    'confidence': 0.7,
                    'source': 'session_context',
                })
        
        return valuable
    
    def _is_important(self, content):
        """判断是否重要"""
        if not content:
            return False
        
        # 重要性关键词
        important_keywords = [
            '决定', '选择', '确定', '最终', '重要', '关键',
            '必须', '不能', '禁止', '警告', '注意',
            '成功', '失败', '错误', '问题', '解决',
        ]
        
        return any(kw in content for kw in important_keywords)
    
    def clear(self):
        """清理会话记忆"""
        self.memory = {
            'session_id': self.session_id,
            'created': datetime.now().isoformat(),
            'task_state': {},
            'temp_decisions': [],
            'intermediate': [],
            'context': [],
        }
        self._save()
    
    def get_summary(self):
        """获取会话摘要"""
        return {
            'session_id': self.session_id,
            'created': self.memory['created'],
            'task_count': len(self.memory['task_state']),
            'decision_count': len(self.memory['temp_decisions']),
            'context_count': len(self.memory['context']),
            'intermediate_count': len(self.memory['intermediate']),
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='会话级记忆管理')
    parser.add_argument('action', choices=['summary', 'compress', 'extract', 'clear'],
                        help='操作类型')
    parser.add_argument('--session-id', default='default',
                        help='会话 ID（默认 default）')
    
    args = parser.parse_args()
    
    session = SessionMemory(args.session_id)
    
    if args.action == 'summary':
        summary = session.get_summary()
        print("📊 会话摘要：")
        print(f"  会话 ID: {summary['session_id']}")
        print(f"  创建时间: {summary['created']}")
        print(f"  任务状态: {summary['task_count']} 项")
        print(f"  临时决策: {summary['decision_count']} 条")
        print(f"  上下文: {summary['context_count']} 条")
        print(f"  中间结果: {summary['intermediate_count']} 条")
    
    elif args.action == 'compress':
        compressed = session.compress()
        print("✅ 已压缩会话记忆")
        print(f"  保留决策: {len(compressed['temp_decisions'])} 条")
        print(f"  保留上下文: {len(compressed['context'])} 条")
    
    elif args.action == 'extract':
        valuable = session.extract_valuable()
        print(f"🔍 提取到 {len(valuable)} 条有价值的记忆：")
        for mem in valuable:
            print(f"  [{mem['confidence']:.2f}|{mem['type']}] {mem['content'][:80]}...")
    
    elif args.action == 'clear':
        session.clear()
        print("✅ 已清理会话记忆")


if __name__ == '__main__':
    main()
