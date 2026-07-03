#!/usr/bin/env python3
"""
DNA Memory - 可视化模块
生成记忆网络的 HTML 可视化
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db


def generate_visualization():
    """生成 HTML 可视化"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有记忆
    cursor.execute("SELECT id, content, type, tags, weight FROM memory WHERE weight > 0.3")
    memories = cursor.fetchall()
    
    # 获取关联
    cursor.execute("SELECT memory_id1, memory_id2, relation_type FROM memory_relations")
    relations = cursor.fetchall()
    
    conn.close()
    
    # 构建节点和边
    nodes = []
    for id_, content, type_, tags, weight in memories:
        nodes.append({
            "id": str(id_),
            "label": content[:30] + "..." if len(content) > 30 else content,
            "type": type_,
            "weight": weight,
            "tags": tags or ""
        })
    
    edges = []
    for id1, id2, rel_type in relations:
        edges.append({
            "from": str(id1),
            "to": str(id2),
            "type": rel_type
        })
    
    # 生成 HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DNA Memory 可视化</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 0; padding: 20px; }}
        #network {{ width: 100%; height: 80vh; border: 1px solid #ddd; }}
        .stats {{ padding: 10px; background: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>🧬 DNA Memory 可视化</h1>
    <div class="stats">
        <strong>节点:</strong> {len(nodes)} | 
        <strong>边:</strong> {len(edges)} | 
        <strong>类型:</strong> 圆形=fact, 方形=preference, 三角=skill
    </div>
    <div id="network"></div>
    <script>
        var nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
        var edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
        var container = document.getElementById('network');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                color: {{
                    background: '#97C2FC',
                    border: '#2B7CE9',
                    highlight: {{ background: '#FFB500', border: '#FFB500' }}
                }},
                font: {{ size: 12 }}
            }},
            edges: {{
                color: '#848484',
                arrows: 'to'
            }},
            physics: {{
                stabilization: false,
                barnesHut: {{ gravitationalConstant: -2000 }}
            }}
        }};
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>'''
    
    output = Path(__file__).parent.parent / "memory" / "visualization.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    print(f"✅ 可视化已生成: {output}")
    return html


if __name__ == "__main__":
    generate_visualization()
