#!/usr/bin/env python3
"""
实时记忆提取器
自动从对话中提取有价值的记忆
"""

import re
import sqlite3
import json
from datetime import datetime
from pathlib import Path

class MemoryExtractor:
    """实时记忆提取器"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        
        # 中文模式匹配
        self.patterns = {
            'correction': [
                r'不是.*?[，,]?\s*是',
                r'应该.*?[，,]?\s*而不是',
                r'错了.*?[，,]?\s*正确的是',
                r'纠正',
                r'改成',
                r'修正',
            ],
            'preference': [
                r'我(喜欢|偏好|希望|想要|需要)',
                r'不要.*?',
                r'以后.*?',
                r'默认.*?',
                r'优先.*?',
                r'必须.*?',
            ],
            'decision': [
                r'决定.*?',
                r'选择.*?',
                r'确定.*?',
                r'最终.*?',
                r'采用.*?',
                r'使用.*?方案',
            ],
            'error': [
                r'失败.*?原因',
                r'错误.*?根因',
                r'问题.*?是',
                r'踩坑',
                r'bug',
                r'报错',
            ],
            'workflow': [
                r'先.*?再.*?',
                r'流程.*?',
                r'步骤.*?',
                r'顺序.*?',
                r'第一.*?第二',
                r'首先.*?然后',
            ],
        }
    
    def extract_from_conversation(self, messages):
        """从对话中提取记忆
        
        Args:
            messages: 对话消息列表，格式 [{'role': 'user', 'content': '...'}]
        
        Returns:
            提取的记忆列表
        """
        memories = []
        
        for msg in messages:
            if msg.get('role') != 'user':
                continue
            
            content = msg.get('content', '')
            if not content:
                continue
            
            # 检测纠正
            if self._match_patterns(content, self.patterns['correction']):
                memories.append({
                    'content': content,
                    'type': 'error',
                    'confidence': 0.9,
                    'source': 'correction',
                })
                continue
            
            # 检测偏好
            if self._match_patterns(content, self.patterns['preference']):
                memories.append({
                    'content': content,
                    'type': 'preference',
                    'confidence': 0.85,
                    'source': 'preference',
                })
                continue
            
            # 检测决策
            if self._match_patterns(content, self.patterns['decision']):
                memories.append({
                    'content': content,
                    'type': 'fact',
                    'confidence': 0.8,
                    'source': 'decision',
                })
                continue
            
            # 检测错误
            if self._match_patterns(content, self.patterns['error']):
                memories.append({
                    'content': content,
                    'type': 'error',
                    'confidence': 0.9,
                    'source': 'error_analysis',
                })
                continue
            
            # 检测工作流程
            if self._match_patterns(content, self.patterns['workflow']):
                memories.append({
                    'content': content,
                    'type': 'pattern',
                    'confidence': 0.75,
                    'source': 'workflow',
                })
                continue
        
        return memories
    
    def _match_patterns(self, content, patterns):
        """匹配模式"""
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def auto_remember(self, memories, threshold=0.7):
        """自动记录高置信度记忆
        
        Args:
            memories: 提取的记忆列表
            threshold: 置信度阈值
        
        Returns:
            记录的记忆数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for mem in memories:
            if mem['confidence'] >= threshold:
                # 检查是否已存在相似记忆
                cursor.execute("""
                    SELECT id FROM memory 
                    WHERE content LIKE ? 
                    LIMIT 1
                """, (f"%{mem['content'][:50]}%",))
                
                if cursor.fetchone():
                    continue  # 跳过重复记忆
                
                # 插入新记忆
                cursor.execute("""
                    INSERT INTO memory (content, type, weight, short_term, long_term, tags)
                    VALUES (?, ?, ?, 1, 0, ?)
                """, (
                    mem['content'], 
                    mem['type'], 
                    mem['confidence'],
                    f"source:{mem['source']},auto_extracted"
                ))
                count += 1
        
        conn.commit()
        conn.close()
        
        return count
    
    def extract_from_file(self, file_path):
        """从对话日志文件中提取记忆
        
        Args:
            file_path: 对话日志文件路径（JSON 格式）
        
        Returns:
            提取的记忆列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = data.get('messages', [])
            return self.extract_from_conversation(messages)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return []


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='实时记忆提取器')
    parser.add_argument('--db', default='~/.openclaw/skills/dna-memory/memory/memory.db',
                        help='数据库路径')
    parser.add_argument('--file', help='对话日志文件路径（JSON 格式）')
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='置信度阈值（默认 0.7）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只提取不写入')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    extractor = MemoryExtractor(str(db_path))
    
    if args.file:
        # 从文件提取
        memories = extractor.extract_from_file(args.file)
        
        print(f"🔍 提取到 {len(memories)} 条记忆：")
        for mem in memories:
            print(f"  [{mem['confidence']:.2f}|{mem['type']}] {mem['content'][:80]}...")
        
        if not args.dry_run:
            count = extractor.auto_remember(memories, args.threshold)
            print(f"✅ 已记录 {count} 条记忆")
    else:
        print("❌ 请指定 --file 参数")


if __name__ == '__main__':
    main()
