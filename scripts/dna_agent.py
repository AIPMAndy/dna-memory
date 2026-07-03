#!/usr/bin/env python3
"""
DNA Memory Agent 集成
让 AI Agent 使用 DNA Memory 进行记忆增强的问答
"""

import sys
from pathlib import Path

# 添加脚本目录到 path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from agent_adapter import AgentAdapter, get_default_agent
from path_utils import get_db_path
import sqlite3
import json


def recall_memories(query: str, limit: int = 5) -> list:
    """从 DNA Memory 检索相关记忆"""
    db_path = str(get_db_path())
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 提取关键词（简单实现：取2-4字的中文词汇）
    import re
    keywords = re.findall(r'[一-龥]{2,4}', query)

    if not keywords:
        # 如果没有中文关键词，使用整句
        search_query = query
    else:
        # 使用第一个关键词
        search_query = keywords[0]

    try:
        # 使用 FTS5 搜索
        cursor.execute("""
            SELECT m.id, m.content, m.type, m.weight, m.created
            FROM memory m
            JOIN memory_fts ON m.id = memory_fts.rowid
            WHERE memory_fts MATCH ?
            ORDER BY m.weight DESC
            LIMIT ?
        """, (search_query, limit))

        results = cursor.fetchall()
    except sqlite3.OperationalError:
        # FTS5 不可用，使用 LIKE
        cursor.execute("""
            SELECT id, content, type, weight, created
            FROM memory
            WHERE content LIKE ?
            ORDER BY weight DESC
            LIMIT ?
        """, (f'%{search_query}%', limit))

        results = cursor.fetchall()

    conn.close()

    return [{
        'id': r[0],
        'content': r[1],
        'type': r[2],
        'weight': r[3],
        'created': r[4]
    } for r in results]


def build_enhanced_prompt(query: str, memories: list) -> str:
    """构建增强后的提示词（包含记忆上下文）"""
    if not memories:
        return query

    # 构建记忆上下文
    memory_context = "📚 相关记忆上下文：\n\n"

    for i, mem in enumerate(memories, 1):
        memory_context += f"{i}. [{mem['type']}] (权重: {mem['weight']:.2f})\n"
        memory_context += f"   {mem['content'][:200]}\n\n"

    # 组合提示词
    enhanced_prompt = f"""{memory_context}
---

基于以上记忆，回答以下问题：

{query}

注意：如果记忆中的信息与问题相关，请优先使用；如果无关，可以忽略。
"""

    return enhanced_prompt


def ask_with_memory(
    query: str,
    agent: str = None,
    model: str = None,
    recall_limit: int = 5,
    verbose: bool = False
) -> dict:
    """
    使用记忆增强的 Agent 问答

    Args:
        query: 用户问题
        agent: Agent 名称（默认自动检测）
        model: 模型名称
        recall_limit: 检索记忆数量
        verbose: 显示详细信息

    Returns:
        {
            'success': bool,
            'response': str,
            'memories_used': int,
            'agent': str,
            'error': str (if failed)
        }
    """
    # 1. 检索相关记忆
    if verbose:
        print(f"🔍 检索相关记忆...")

    memories = recall_memories(query, limit=recall_limit)

    if verbose:
        print(f"   找到 {len(memories)} 条相关记忆")

    # 2. 构建增强提示词
    if memories:
        enhanced_query = build_enhanced_prompt(query, memories)
        if verbose:
            print(f"   已将记忆注入上下文")
    else:
        enhanced_query = query
        if verbose:
            print(f"   未找到相关记忆，直接提问")

    # 3. 选择 Agent
    agent_name = agent or get_default_agent()

    if not agent_name:
        return {
            'success': False,
            'error': '未找到可用的 Agent',
            'memories_used': len(memories)
        }

    if verbose:
        print(f"🤖 使用 {agent_name} 回答...")

    # 4. 调用 Agent
    try:
        adapter = AgentAdapter(agent_name)
        result = adapter.call(enhanced_query, model=model)

        return {
            'success': result['success'],
            'response': result.get('response'),
            'memories_used': len(memories),
            'agent': agent_name,
            'error': result.get('error')
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'调用 Agent 失败: {str(e)}',
            'memories_used': len(memories),
            'agent': agent_name
        }


# ============ CLI ============
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='DNA Memory Agent - 使用记忆增强的 AI 问答',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 基础问答（自动检索记忆）
  python3 scripts/dna_agent.py "如何使用飞书 API？"

  # 指定 Agent
  python3 scripts/dna_agent.py "如何调试错误？" --agent hermes

  # 指定模型
  python3 scripts/dna_agent.py "写一个函数" --agent claude --model opus

  # 显示详细信息
  python3 scripts/dna_agent.py "用户偏好是什么？" -v
        """
    )

    parser.add_argument('query', help='问题或提示词')
    parser.add_argument('--agent', choices=['claude', 'hermes'], help='指定 Agent')
    parser.add_argument('--model', help='指定模型')
    parser.add_argument('--limit', type=int, default=5, help='检索记忆数量（默认5）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')

    args = parser.parse_args()

    # 执行问答
    result = ask_with_memory(
        query=args.query,
        agent=args.agent,
        model=args.model,
        recall_limit=args.limit,
        verbose=args.verbose
    )

    # 显示结果
    if result['success']:
        if args.verbose:
            print(f"\n{'='*60}")
            print(f"✅ 回答（使用了 {result['memories_used']} 条记忆）：")
            print(f"{'='*60}\n")

        print(result['response'])

        if args.verbose:
            print(f"\n{'='*60}")
            print(f"Agent: {result['agent']}")
    else:
        print(f"❌ 失败: {result['error']}")
        if args.verbose:
            print(f"   检索到 {result['memories_used']} 条记忆")
        sys.exit(1)


if __name__ == '__main__':
    main()
