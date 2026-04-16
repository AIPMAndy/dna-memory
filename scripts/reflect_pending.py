#!/usr/bin/env python3
"""
反思待晋升记忆 - 定期检查待反思的记忆，提升置信度后写入 DNA Memory
"""

import json
import subprocess
import os
from datetime import datetime

PENDING_FILE = "/tmp/dna_memory_pending.json"

def reflect_pending_memories():
    """反思待晋升记忆"""
    if not os.path.exists(PENDING_FILE):
        print("ℹ️  没有待反思的记忆文件")
        return
    
    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        memories = json.load(f)
    
    if not memories:
        print("ℹ️  待反思记忆列表为空")
        return
    
    print(f"🔄 开始反思 {len(memories)} 条待晋升记忆...\n")
    
    promoted_count = 0
    for memory in memories:
        # 简单策略：如果记忆存在超过 24 小时且无负面反馈，提升置信度
        # 实际可以引入更复杂的评估（如用户反馈、使用频率等）
        
        original_confidence = memory['confidence']
        new_confidence = min(original_confidence + 0.1, 0.95)  # 每次提升 0.1
        
        if new_confidence >= 0.8:
            cmd = [
                "python3",
                os.path.expanduser("~/.openclaw/skills/dna-memory/scripts/evolve.py"),
                "remember",
                memory['content'],
                "-t", memory['type'],
                "-i", str(new_confidence)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
                if result.returncode == 0:
                    promoted_count += 1
                    print(f"✅ [已晋升] {memory['content'][:50]}... ({original_confidence:.2f} → {new_confidence:.2f})")
                else:
                    print(f"❌ 保存失败：{result.stderr}")
            except Exception as e:
                print(f"❌ 执行错误：{e}")
        else:
            print(f"⏳ [继续等待] {memory['content'][:50]}... ({original_confidence:.2f} → {new_confidence:.2f})")
    
    print(f"\n📊 本次反思：晋升 {promoted_count} 条，继续等待 {len(memories) - promoted_count} 条")
    
    # 更新待反思列表（移除已晋升的）
    remaining = [m for m in memories if m['confidence'] + 0.1 < 0.8]
    if remaining:
        with open(PENDING_FILE, 'w', encoding='utf-8') as f:
            json.dump(remaining, f, ensure_ascii=False, indent=2)
    else:
        os.remove(PENDING_FILE)
        print("🗑️  待反思文件已删除")

if __name__ == "__main__":
    reflect_pending_memories()
