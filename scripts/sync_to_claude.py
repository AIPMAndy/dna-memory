#!/usr/bin/env python3
"""
优化版 sync_to_claude.py
- 只同步高权重记忆，控制数量
- 优先同步最近使用的记忆
- 生成轻量级的同步文件
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

# Legacy database path. Override it instead of editing this file.
DNA_MEMORY_DB = Path(os.getenv(
    "DNA_MEMORY_LEGACY_DB",
    Path(__file__).resolve().parents[1] / "memory" / "memory.db",
)).expanduser()

# Claude Code memory target. Project-specific locations vary by installation.
CLAUDE_MEMORY_DIR = Path(os.getenv(
    "CLAUDE_MEMORY_DIR",
    Path.home() / ".claude" / "memory",
)).expanduser()
CLAUDE_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Optional legacy configuration. Runtime configuration stays outside the repo.
CONFIG_FILE = Path(os.getenv(
    "DNA_MEMORY_LEGACY_CONFIG",
    Path.home() / ".config" / "dna-memory" / "legacy-config.json",
)).expanduser()

def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'sync_weight_threshold': 0.8,
        'sync_max_memories': 20,
        'sync_prefer_recent': True
    }

def get_high_priority_memories():
    """获取高优先级记忆（优化版）"""
    config = load_config()
    weight_threshold = config.get('sync_weight_threshold', 0.8)
    max_memories = config.get('sync_max_memories', 20)
    prefer_recent = config.get('sync_prefer_recent', True)

    conn = sqlite3.connect(str(DNA_MEMORY_DB))
    cursor = conn.cursor()

    # 优化查询：只取需要的字段，使用索引排序
    order_clause = "last_accessed DESC" if prefer_recent else "weight DESC"

    cursor.execute(f"""
        SELECT id, content, type, weight, tags, last_accessed
        FROM memory
        WHERE (weight >= ? OR type = 'preference')
          AND long_term = 0
        ORDER BY {order_clause}
        LIMIT ?
    """, (weight_threshold, max_memories))

    memories = []
    for row in cursor.fetchall():
        memories.append({
            'id': row[0],
            'content': row[1],
            'type': row[2],
            'weight': row[3],
            'tags': row[4],
            'last_accessed': row[5]
        })

    conn.close()
    return memories

def sync_to_claude_memory():
    """同步高优先级记忆到 Claude Memory（优化版）"""
    memories = get_high_priority_memories()

    if not memories:
        print("❌ 没有找到高优先级记忆")
        return

    # 按类型分组
    preferences = [m for m in memories if m['type'] == 'preference']
    patterns = [m for m in memories if m['type'] == 'pattern']
    skills = [m for m in memories if m['type'] == 'skill']
    errors = [m for m in memories if m['type'] == 'error']

    # 生成精简的 critical-preferences.md（只包含最重要的）
    if preferences:
        content = f"""---
name: critical-preferences
description: High-priority preferences synced from DNA Memory
metadata:
  type: preference
  synced_at: {datetime.now().isoformat()}
  source: dna-memory
  count: {len(preferences)}
---

# Critical Preferences

**自动同步自 DNA Memory**（权重 ≥ 0.8 的偏好）
**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        for i, mem in enumerate(preferences, 1):
            # 截断过长的内容
            content_text = mem['content']
            if len(content_text) > 200:
                content_text = content_text[:200] + "..."

            content += f"## {i}. {mem['type'].capitalize()} (权重 {mem['weight']:.2f})\n\n"
            content += f"{content_text}\n\n"
            content += "---\n\n"

        target = CLAUDE_MEMORY_DIR / "synced-preferences.md"
        target.write_text(content, encoding='utf-8')
        print(f"✅ 同步了 {len(preferences)} 条偏好")

    # 生成精简的 learned-patterns.md
    if patterns or skills or errors:
        content = f"""---
name: learned-patterns
description: Learned patterns and skills from experience
metadata:
  type: project
  synced_at: {datetime.now().isoformat()}
  source: dna-memory
  count: {len(patterns) + len(skills) + len(errors)}
---

# Learned Patterns & Skills

**自动同步自 DNA Memory**（高权重的模式和技能）
**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        if patterns:
            content += "## 工作模式\n\n"
            for mem in patterns[:5]:  # 最多5条
                content_text = mem['content'][:150] + ("..." if len(mem['content']) > 150 else "")
                content += f"- **[{mem['weight']:.2f}]** {content_text}\n\n"

        if skills:
            content += "## 学到的技能\n\n"
            for mem in skills[:5]:
                content_text = mem['content'][:150] + ("..." if len(mem['content']) > 150 else "")
                content += f"- **[{mem['weight']:.2f}]** {content_text}\n\n"

        if errors:
            content += "## 错误教训\n\n"
            for mem in errors[:5]:
                content_text = mem['content'][:150] + ("..." if len(mem['content']) > 150 else "")
                content += f"- **[{mem['weight']:.2f}]** {content_text}\n\n"

        target = CLAUDE_MEMORY_DIR / "synced-patterns.md"
        target.write_text(content, encoding='utf-8')
        print(f"✅ 同步了 {len(patterns) + len(skills) + len(errors)} 条模式/技能/教训")

    # 更新 MEMORY.md 索引（如果不存在）
    memory_index = CLAUDE_MEMORY_DIR / "MEMORY.md"
    if memory_index.exists():
        existing = memory_index.read_text(encoding='utf-8')
    else:
        existing = "# Memory Index\n\n## High Priority\n"

    # 确保索引包含同步的文件
    if "synced-preferences.md" not in existing and preferences:
        existing += "- [Synced Preferences](synced-preferences.md) — DNA Memory 高优先级偏好（自动同步）\n"

    if "synced-patterns.md" not in existing and (patterns or skills or errors):
        existing += "- [Synced Patterns](synced-patterns.md) — DNA Memory 学习模式（自动同步）\n"

    memory_index.write_text(existing, encoding='utf-8')

    # 生成统计
    total = len(memories)
    print(f"\n📊 同步统计:")
    print(f"   - 总计: {total} 条高优先级记忆")
    print(f"   - 偏好: {len(preferences)} 条")
    print(f"   - 模式: {len(patterns)} 条")
    print(f"   - 技能: {len(skills)} 条")
    print(f"   - 错误: {len(errors)} 条")

    # 生成同步元数据
    sync_meta = {
        'synced_at': datetime.now().isoformat(),
        'total_memories': total,
        'by_type': {
            'preference': len(preferences),
            'pattern': len(patterns),
            'skill': len(skills),
            'error': len(errors),
        }
    }

    meta_file = CLAUDE_MEMORY_DIR / ".sync-meta.json"
    meta_file.write_text(json.dumps(sync_meta, indent=2), encoding='utf-8')

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DNA Memory Bridge - 优化版同步")
    parser.add_argument("--dry-run", action="store_true", help="预览但不写入")
    args = parser.parse_args()

    if args.dry_run:
        memories = get_high_priority_memories()
        print(f"🔍 找到 {len(memories)} 条高优先级记忆:")
        for m in memories:
            print(f"   [{m['weight']:.2f}|{m['type']}] {m['content'][:80]}...")
    else:
        sync_to_claude_memory()
