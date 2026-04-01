#!/usr/bin/env python3
"""
DNA Memory - 语义搜索模块
用 Embeddings 实现相似记忆搜索
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time


EMBEDDINGS_FILE = Path(__file__).parent.parent / "memory" / "embeddings.json"


def get_embedding(text, provider="openai"):
    """获取文本的 embedding"""
    import os
    
    # OpenAI
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import requests
                resp = requests.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": "text-embedding-3-small", "input": text[:8000]},
                    timeout=30
                )
                if resp.status_code == 200:
                    return resp.json()["data"][0]["embedding"]
            except:
                pass
    
    # 本地简单 hash（备用）
    return simple_hash(text)


def simple_hash(text):
    """简单的 hash 作为备用 embedding"""
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    return list(h[:32]) + [0] * 96  # 补齐到 128 维


def cosine_similarity(a, b):
    """计算余弦相似度（纯 Python 实现，避免强依赖 numpy）。"""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    a_vals = [float(x) for x in a[:n]]
    b_vals = [float(x) for x in b[:n]]
    dot = sum(x * y for x, y in zip(a_vals, b_vals))
    norm_a = sum(x * x for x in a_vals) ** 0.5
    norm_b = sum(y * y for y in b_vals) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b + 1e-8)


def load_embeddings():
    """加载已有的 embeddings"""
    if EMBEDDINGS_FILE.exists():
        return json.loads(EMBEDDINGS_FILE.read_text())
    return {}


def save_embeddings(embeddings):
    """保存 embeddings"""
    EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_FILE.write_text(json.dumps(embeddings, ensure_ascii=False))


def build_embeddings(limit=100):
    """为所有记忆构建 embeddings"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, content FROM memory ORDER BY created DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    embeddings = load_embeddings()
    new_count = 0
    
    for id_, content in rows:
        if str(id_) not in embeddings:
            emb = get_embedding(content)
            embeddings[str(id_)] = emb
            new_count += 1
    
    save_embeddings(embeddings)
    return new_count


def semantic_search(query, top_k=5, min_similarity=0.5):
    """语义搜索相似记忆"""
    # 获取 query 的 embedding
    query_emb = get_embedding(query)
    
    # 加载所有 embeddings
    embeddings = load_embeddings()
    if not embeddings:
        return []
    
    # 获取记忆内容
    conn = get_db()
    cursor = conn.cursor()
    
    results = []
    for id_, emb in embeddings.items():
        sim = cosine_similarity(query_emb, emb)
        if sim >= min_similarity:
            cursor.execute("SELECT content, type, tags, weight FROM memory WHERE id = ?", (int(id_),))
            row = cursor.fetchone()
            if row:
                results.append({
                    "id": id_,
                    "content": row[0],
                    "type": row[1],
                    "tags": row[2],
                    "weight": row[3],
                    "similarity": sim
                })
    
    conn.close()
    
    # 排序并返回 top_k
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "search"])
    parser.add_argument("--query", help="搜索query")
    parser.add_argument("--top", type=int, default=5, help="返回数量")
    args = parser.parse_args()
    
    if args.command == "build":
        n = build_embeddings()
        print(f"✅ 构建了 {n} 个新 embeddings")
    elif args.command == "search":
        results = semantic_search(args.query, top_k=args.top)
        print(f"🔍 搜索: {args.query}")
        for r in results:
            print(f"   [{r['similarity']:.2f}] {r['content'][:50]}...")
