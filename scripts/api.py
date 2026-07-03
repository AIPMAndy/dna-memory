#!/usr/bin/env python3
"""
DNA Memory - API 服务模块
提供 HTTP API 供外部调用
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
from scripts.evolve import add_working_memory, get_working_memory
from scripts.semantic_search import semantic_search
import time


def handle_request(req):
    """处理 API 请求"""
    action = req.get("action")
    
    if action == "remember":
        content = req.get("content")
        mem_type = req.get("type", "fact")
        importance = req.get("importance", 0.6)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
            VALUES (?, ?, 'api', ?, 1, 0, ?, ?)
        """, (content, mem_type, importance, time.time(), time.time()))
        conn.commit()
        conn.close()
        
        return {"status": "ok", "message": f"已记录: {content}"}
    
    elif action == "recall":
        query = req.get("query", "")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 精确匹配
        cursor.execute("SELECT content, type, weight FROM memory WHERE content LIKE ?", (f"%{query}%",))
        results = [{"content": r[0], "type": r[1], "weight": r[2]} for r in cursor.fetchall()]
        
        conn.close()
        
        # 语义搜索补充
        semantic = semantic_search(query, top_k=3)
        for s in semantic:
            if s["content"] not in [r["content"] for r in results]:
                results.append({"content": s["content"], "type": "semantic", "weight": s["similarity"]})
        
        return {"status": "ok", "results": results[:10]}
    
    elif action == "working":
        if req.get("add"):
            add_working_memory(req["add"], req.get("importance", 0.8))
            return {"status": "ok", "message": "已添加到工作记忆"}
        else:
            return {"status": "ok", "working": get_working_memory()}
    
    elif action == "stats":
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memory")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memory WHERE short_term = 1")
        short_term = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memory WHERE long_term = 1")
        long_term = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(weight) FROM memory")
        avg_weight = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {"status": "ok", "stats": {
            "total": total,
            "short_term": short_term,
            "long_term": long_term,
            "avg_weight": round(avg_weight, 3)
        }}
    
    else:
        return {"status": "error", "message": f"未知动作: {action}"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765, help="服务端口")
    args = parser.parse_args()
    
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
    except ImportError:
        print("❌ 需要安装 http.server (Python 3 内置)")
        sys.exit(1)
    
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode())
            
            resp = handle_request(req)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())
        
        def log_message(self, format, *args):
            pass  # 静默日志
    
    print(f"🚀 DNA Memory API 服务启动: http://localhost:{args.port}")
    server = HTTPServer(('', args.port), Handler)
    server.serve_forever()
