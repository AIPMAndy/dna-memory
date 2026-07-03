#!/usr/bin/env python3
"""
Memory Compression - 记忆压缩系统
功能：
- 压缩低频访问的长期记忆
- 保留关键信息摘要
- 原始内容归档到冷存储
- 需要时可以解压恢复
"""

import json
import sqlite3
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import re

# ============ 配置 ============
MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"
ARCHIVE_DIR = MEMORY_DIR / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

# 压缩阈值
LOW_ACCESS_THRESHOLD = 3  # 访问次数阈值
AGE_THRESHOLD_DAYS = 90   # 年龄阈值（天）


# ============ 关键信息提取 ============
def extract_key_points(content: str, max_length: int = 100) -> str:
    """提取关键信息"""
    # 简单策略：
    # 1. 如果内容短，直接返回
    if len(content) <= max_length:
        return content
    
    # 2. 提取关键句（包含动词、数字、专有名词）
    sentences = re.split(r'[。！？\n]', content)
    
    key_sentences = []
    for sentence in sentences:
        # 包含数字
        if re.search(r'\d', sentence):
            key_sentences.append(sentence)
            continue
        
        # 包含动词
        action_words = ['做', '用', '执行', '调用', '运行', '检查', '优化', '修复', '避免', '不要']
        if any(word in sentence for word in action_words):
            key_sentences.append(sentence)
            continue
        
        # 包含专有名词（大写字母开头）
        if re.search(r'[A-Z][a-z]+', sentence):
            key_sentences.append(sentence)
    
    # 3. 如果没有关键句，取前 max_length 字符
    if not key_sentences:
        return content[:max_length] + '...'
    
    # 4. 拼接关键句
    summary = '。'.join(key_sentences)
    
    if len(summary) > max_length:
        return summary[:max_length] + '...'
    
    return summary


# ============ 归档 ============
def archive_to_cold_storage(memory: Dict) -> str:
    """归档到冷存储"""
    # 生成文件名（基于 ID 和时间戳）
    filename = f"memory_{memory['id']}_{int(time.time())}.json"
    filepath = ARCHIVE_DIR / filename
    
    # 保存完整内容
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


def restore_from_archive(memory_id: int, archive_path: str) -> Optional[Dict]:
    """从归档恢复"""
    try:
        with open(archive_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
        return None


# ============ 压缩 ============
def compress_memory(memory: Dict, dry_run: bool = True) -> Dict:
    """压缩单个记忆"""
    # 提取关键信息
    summary = extract_key_points(memory['content'])
    
    # 计算内容哈希
    content_hash = hashlib.sha256(memory['content'].encode()).hexdigest()
    
    compressed = {
        'id': memory['id'],
        'summary': summary,
        'type': memory['type'],
        'tags': memory['tags'],
        'weight': memory['weight'],
        'content_hash': content_hash,
        'compressed': True,
        'original_length': len(memory['content']),
        'compressed_length': len(summary),
        'compression_ratio': 1 - len(summary) / len(memory['content'])
    }
    
    if not dry_run:
        # 归档原始内容
        archive_path = archive_to_cold_storage(memory)
        compressed['archive_path'] = archive_path
        
        # 更新数据库
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE memory
            SET content = ?, tags = ?
            WHERE id = ?
        """, (
            json.dumps(compressed),  # 存储压缩信息
            memory['tags'] + ',compressed',
            memory['id']
        ))
        
        # 记录压缩操作
        cursor.execute("""
            INSERT INTO operations (operation, details)
            VALUES (?, ?)
        """, ('compress', json.dumps({
            'memory_id': memory['id'],
            'original_length': compressed['original_length'],
            'compressed_length': compressed['compressed_length'],
            'compression_ratio': compressed['compression_ratio'],
            'archive_path': archive_path
        })))
        
        conn.commit()
        conn.close()
    
    return compressed


# ============ 解压 ============
def decompress_memory(memory_id: int) -> Optional[Dict]:
    """解压记忆"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 获取压缩记忆
    cursor.execute("""
        SELECT content, tags FROM memory
        WHERE id = ? AND tags LIKE '%compressed%'
    """, (memory_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    try:
        compressed_data = json.loads(row[0])
    except:
        conn.close()
        return None
    
    # 从归档恢复
    archive_path = compressed_data.get('archive_path')
    if not archive_path:
        conn.close()
        return None
    
    original = restore_from_archive(memory_id, archive_path)
    if not original:
        conn.close()
        return None
    
    # 恢复到数据库
    cursor.execute("""
        UPDATE memory
        SET content = ?, tags = ?
        WHERE id = ?
    """, (
        original['content'],
        row[1].replace(',compressed', ''),
        memory_id
    ))
    
    # 记录解压操作
    cursor.execute("""
        INSERT INTO operations (operation, details)
        VALUES (?, ?)
    """, ('decompress', json.dumps({
        'memory_id': memory_id,
        'archive_path': archive_path
    })))
    
    conn.commit()
    conn.close()
    
    return original


# ============ 批量压缩 ============
def find_compressible_memories() -> List[Dict]:
    """找到可压缩的记忆"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 找到低频访问的长期记忆
    cutoff_time = time.time() - (AGE_THRESHOLD_DAYS * 86400)
    
    cursor.execute("""
        SELECT id, content, type, tags, weight, created, updated
        FROM memory
        WHERE long_term = 1
        AND tags NOT LIKE '%compressed%'
        AND created < ?
        AND LENGTH(content) > 100
    """, (cutoff_time,))
    
    candidates = []
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
        
        # 计算访问频率（基于 updated 时间）
        days_since_update = (time.time() - memory['updated']) / 86400
        
        if days_since_update > 30:  # 30 天未访问
            candidates.append(memory)
    
    conn.close()
    
    return candidates


def batch_compress(dry_run: bool = True) -> List[Dict]:
    """批量压缩"""
    candidates = find_compressible_memories()
    
    results = []
    for memory in candidates:
        compressed = compress_memory(memory, dry_run)
        results.append(compressed)
    
    return results


# ============ 统计 ============
def analyze_compression_potential() -> Dict:
    """分析压缩潜力"""
    candidates = find_compressible_memories()
    
    total_size = sum(len(m['content']) for m in candidates)
    
    # 估算压缩后大小
    estimated_compressed_size = 0
    for memory in candidates:
        summary = extract_key_points(memory['content'])
        estimated_compressed_size += len(summary)
    
    savings = total_size - estimated_compressed_size
    compression_ratio = savings / total_size if total_size > 0 else 0
    
    return {
        'compressible_count': len(candidates),
        'total_size': total_size,
        'estimated_compressed_size': estimated_compressed_size,
        'estimated_savings': savings,
        'compression_ratio': compression_ratio,
        'top_candidates': [
            {
                'id': m['id'],
                'content_preview': m['content'][:60] + '...',
                'size': len(m['content']),
                'age_days': (time.time() - m['created']) / 86400
            }
            for m in candidates[:10]
        ]
    }


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(description='Memory Compression - 记忆压缩')
    parser.add_argument('action', choices=['analyze', 'compress', 'decompress'], help='操作类型')
    parser.add_argument('--id', type=int, help='记忆 ID（用于 decompress）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式')
    
    args = parser.parse_args()
    
    if args.action == 'analyze':
        stats = analyze_compression_potential()
        
        print(f"\n📊 压缩潜力分析\n")
        print(f"可压缩记忆数: {stats['compressible_count']}")
        print(f"总大小: {stats['total_size']:,} 字符")
        print(f"压缩后大小: {stats['estimated_compressed_size']:,} 字符")
        print(f"可节省: {stats['estimated_savings']:,} 字符")
        print(f"压缩率: {stats['compression_ratio']:.1%}")
        
        if stats['top_candidates']:
            print(f"\nTop 10 候选:")
            for i, c in enumerate(stats['top_candidates'], 1):
                print(f"{i}. [ID:{c['id']}] {c['content_preview']}")
                print(f"   大小: {c['size']} 字符 | 年龄: {c['age_days']:.0f} 天")
    
    elif args.action == 'compress':
        results = batch_compress(dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"\n🔍 预览模式：将压缩 {len(results)} 条记忆\n")
            
            total_savings = sum(r['original_length'] - r['compressed_length'] for r in results)
            
            for i, r in enumerate(results[:10], 1):
                print(f"{i}. [ID:{r['id']}]")
                print(f"   原始: {r['original_length']} 字符")
                print(f"   压缩: {r['compressed_length']} 字符")
                print(f"   压缩率: {r['compression_ratio']:.1%}")
                print()
            
            print(f"总节省: {total_savings:,} 字符")
            print("\n使用 --no-dry-run 执行实际压缩")
        else:
            print(f"\n✅ 已压缩 {len(results)} 条记忆\n")
            
            total_savings = sum(r['original_length'] - r['compressed_length'] for r in results)
            print(f"总节省: {total_savings:,} 字符")
    
    elif args.action == 'decompress':
        if not args.id:
            print("❌ 需要指定 --id")
            return
        
        original = decompress_memory(args.id)
        
        if original:
            print(f"\n✅ 已解压记忆 {args.id}")
            print(f"   内容: {original['content'][:100]}...")
        else:
            print(f"❌ 记忆 {args.id} 不存在或未压缩")


if __name__ == '__main__':
    main()
