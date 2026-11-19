#!/usr/bin/env python3
"""Independent, local-first content graph MVP. Python stdlib only."""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib import request

TYPES = {"QST": "问题", "CON": "概念", "OPI": "观点", "CAS": "案例", "SOL": "方案"}
LABELS = {v: k for k, v in TYPES.items()}
LABELS.update({k: k for k in TYPES})
RELATIONS = {"回应", "解释", "证明", "冲突"}
SKIP = {".git", ".venv", "node_modules", "__pycache__", ".trash", "secrets"}
MARKER = re.compile(r"^\s*(?:[-*]\s*)?(问题|概念|观点|案例|方案|QST|CON|OPI|CAS|SOL)[：:]\s*(\S.*?)\s*$")
SENSITIVE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|-----BEGIN .*PRIVATE KEY|password\s*[=:]|api[_-]?key\s*[=:])", re.I)

def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)

def store(root):
    return [read(root / "sources.json", {}), read(root / "units.json", {}), read(root / "links.json", [])]

def persist(root, sources, units, links):
    for filename, data in (("sources.json", sources), ("units.json", units), ("links.json", links)):
        write(root / filename, data)

def ingest(root, folder):
    if not folder.is_dir():
        raise ValueError("input folder not found")
    sources, units, links = store(root)
    changed = 0
    for file in sorted(folder.resolve().rglob("*")):
        if not file.is_file() or file.is_symlink() or file.suffix.lower() not in {".txt", ".md"}:
            continue
        if any(part.startswith(".") or part in SKIP for part in file.relative_to(folder.resolve()).parts):
            continue
        if file.stat().st_size > 512 * 1024:
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SENSITIVE.search(content):
            continue
        sid = "SRC-" + sha(str(file))
        record = {"id": sid, "path": str(file), "sha": sha(content)}
        if sid not in sources or sources[sid]["sha"] != record["sha"]:
            sources[sid] = record
            changed += 1
    persist(root, sources, units, links)
    return {"changed_sources": changed, "total_sources": len(sources)}

def ai_proposals(content, model, base):
    if SENSITIVE.search(content):
        raise ValueError("possible credential; document refused")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is required for AI extraction")
    if not base.startswith("https://"):
        raise ValueError("AI endpoint must use HTTPS")
    instruction = ('Return only JSON {"units":[{"type":"QST|CON|OPI|CAS|SOL",'
                   '"quote":"verbatim substring","claim":"brief statement"}]}. '
                   'Extract no more than 20 evidence-grounded units. Never invent evidence.')
    body = {"model": model, "temperature": 0, "messages": [
        {"role": "system", "content": instruction},
        {"role": "user", "content": content[:12000]}]}
    req = request.Request(base.rstrip("/") + "/chat/completions",
                          data=json.dumps(body).encode("utf-8"),
                          headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                                   "Content-Type": "application/json"})
    with request.urlopen(req, timeout=60) as response:
        result = json.load(response)
    raw = result["choices"][0]["message"]["content"]
    parsed = json.loads(raw)
    for item in parsed.get("units", [])[:20]:
        if not isinstance(item, dict) or item.get("type") not in TYPES:
            continue
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote or quote not in content:
            continue
        line = content[:content.index(quote)].count("\n") + 1
        yield {"type": item["type"], "quote": quote,
               "claim": str(item.get("claim") or quote)[:500], "line": line}

def marker_proposals(content):
    for line, text in enumerate(content.splitlines(), 1):
        m = MARKER.match(text)
        if m and m.group(2):
            yield {"type": LABELS[m.group(1)], "quote": m.group(2),
                   "claim": m.group(2), "line": line}

def extract(root, mode, model, base, upload):
    if mode == "ai" and not upload:
        raise ValueError("External AI requires --allow-external-upload")
    sources, units, links = store(root)
    added = 0
    for src in sources.values():
        file = Path(src["path"])
        if not file.is_file():
            continue
        content = file.read_text(encoding="utf-8")
        if sha(content) != src["sha"]:
            src["sha"] = sha(content)
        if src.get("processed_sha") == src["sha"] and src.get("mode") == mode:
            continue
        proposals = (marker_proposals(content) if mode == "markers"
                     else ai_proposals(content, model, base))
        new_nodes = list(proposals)
        for u in units.values():
            if u["source_id"] == src["id"]:
                u["stale"] = True
        for u in new_nodes:
            uid = u["type"] + "-" + sha(src["id"] + u["type"] + u["quote"])
            prior = units.get(uid, {})
            units[uid] = {"id": uid, "type": u["type"], "claim": u["claim"],
                          "quote": u["quote"], "source_id": src["id"],
                          "line": u["line"], "review": prior.get("review", "draft"),
                          "stale": False}
            added += not bool(prior)
        src["processed_sha"] = src["sha"]
        src["mode"] = mode
    persist(root, sources, units, links)
    return {"new_nodes": added, "active_nodes": sum(not u["stale"] for u in units.values())}

def approve(root, uid):
    sources, units, links = store(root)
    if uid not in units or units[uid]["stale"]:
        raise ValueError("node not found or stale")
    units[uid]["review"] = "approved"
    persist(root, sources, units, links)
    return {"approved": uid}

def link(root, a, kind, b, evidence):
    sources, units, links = store(root)
    if kind not in RELATIONS or not evidence.strip() or a == b:
        raise ValueError("invalid link")
    if any(k not in units or units[k]["stale"] or units[k]["review"] != "approved" for k in (a, b)):
        raise ValueError("both nodes must be approved and active")
    edge = {"from": a, "to": b, "relation": kind, "evidence": evidence.strip()}
    if edge not in links:
        links.append(edge)
    persist(root, sources, units, links)
    return edge

def validate(root):
    sources, units, links = store(root)
    errors = []
    for uid, u in units.items():
        src = sources.get(u["source_id"])
        if not src:
            errors.append(uid + ": source missing")
            continue
        if u["stale"]:
            continue
        try:
            content = Path(src["path"]).read_text(encoding="utf-8")
            if u["quote"] not in content:
                errors.append(uid + ": evidence not present")
        except OSError:
            errors.append(uid + ": unreadable source")
    for edge in links:
        if any(k not in units or units[k]["stale"] or units[k]["review"] != "approved"
               for k in (edge["from"], edge["to"])):
            errors.append("invalid relationship " + edge["from"] + "->" + edge["to"])
    return {"sources": len(sources), "units": len(units),
            "approved_active": sum(u["review"] == "approved" and not u["stale"] for u in units.values()),
            "links": len(links), "errors": errors, "ok": not errors}

def graph(root, output):
    _, units, links = store(root)
    nodes = [u for u in units.values() if not u["stale"]][:120]
    positions = {u["id"]: (400 + 275 * math.cos(i * 2 * math.pi / max(1, len(nodes))),
                            320 + 265 * math.sin(i * 2 * math.pi / max(1, len(nodes))))
                 for i, u in enumerate(nodes)}
    colors = {"QST": "#60a5fa", "CON": "#a78bfa", "OPI": "#22d3ee",
              "CAS": "#fbbf24", "SOL": "#4ade80"}
    svg = ['<svg viewBox="0 0 800 650" role="img" aria-label="知识关系图">']
    for edge in links:
        a, b = positions.get(edge["from"]), positions.get(edge["to"])
        if a and b:
            svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#6b7280"/>' % (*a, *b))
    for u in nodes:
        x, y = positions[u["id"]]
        svg.append('<a href="#%s"><circle cx="%.1f" cy="%.1f" r="10" fill="%s"><title>%s</title></circle></a>' %
                   (u["id"], x, y, colors[u["type"]], html.escape(u["claim"])))
    svg.append('</svg>')
    cards = []
    for u in nodes:
        cards.append('<article id="%s"><b>%s · %s</b><p>%s</p><small>%s 行 %d · %s</small></article>' %
                     (u["id"], u["id"], TYPES[u["type"]], html.escape(u["claim"]),
                      u["source_id"], u["line"], u["review"]))
    doc = ('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
           '<title>Content Knowledge Graph</title><style>body{background:#0c1423;color:#e2e8f0;'
           'font:15px system-ui;max-width:1050px;margin:auto;padding:24px}svg{width:100%;height:auto;'
           'background:#142037;border-radius:18px}article{padding:14px;border-bottom:1px solid #304055}'
           'a{cursor:pointer}small{color:#8fa6ba}</style><h1>Content Knowledge Graph</h1>'
           '<p>本地只读可视化 · 前 120 个活动节点 · 仅展示人工审核关系</p>'
           + ''.join(svg) + '<h2>节点与来源</h2>' + ''.join(cards) + '</html>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(doc, encoding="utf-8")
    return {"output": str(output), "nodes_displayed": len(nodes)}

def assemble(root, output, drafts):
    sources, units, links = store(root)
    chosen = [u for u in units.values() if not u["stale"] and (drafts or u["review"] == "approved")]
    lines = ["# 可追溯选题装配稿", "", "> 此稿不是自动生成的事实；原文证据与人工审核优先。", ""]
    for kind, label in TYPES.items():
        lines.extend(["## " + label, ""])
        for u in chosen:
            if u["type"] == kind:
                lines.append("- %s — %s （%s:%s，%s）" % (
                    u["id"], u["claim"], sources[u["source_id"]]["path"], u["line"], u["review"]))
        lines.append("")
    lines.extend(["## 人工审核的关系", ""])
    lines.extend("- %s —%s→ %s（%s）" % (e["from"], e["relation"], e["to"], e["evidence"]) for e in links)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"output": str(output), "included_nodes": len(chosen)}

def main():
    p = argparse.ArgumentParser(description="Evidence-linked, local-first knowledge graph")
    p.add_argument("--workspace", type=Path, default=Path("./workspace"))
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("validate")
    a = sub.add_parser("ingest"); a.add_argument("folder", type=Path)
    a = sub.add_parser("extract"); a.add_argument("--mode", choices=["markers", "ai"], default="markers")
    a.add_argument("--model", default="gpt-4.1-mini")
    a.add_argument("--base-url", default="https://api.openai.com/v1")
    a.add_argument("--allow-external-upload", action="store_true")
    a = sub.add_parser("approve"); a.add_argument("id")
    a = sub.add_parser("link"); a.add_argument("from_id"); a.add_argument("relation", choices=sorted(RELATIONS))
    a.add_argument("to_id"); a.add_argument("--evidence", required=True)
    a = sub.add_parser("search"); a.add_argument("keyword")
    a = sub.add_parser("graph"); a.add_argument("--out", type=Path, default=Path("workspace/graph.html"))
    a = sub.add_parser("assemble"); a.add_argument("--out", type=Path, default=Path("workspace/assembly.md"))
    a.add_argument("--include-drafts", action="store_true")
    args = p.parse_args(); root = args.workspace.resolve(); root.mkdir(parents=True, exist_ok=True)
    try:
        if args.action == "ingest": result = ingest(root, args.folder)
        elif args.action == "extract":
            result = extract(root, args.mode, args.model, args.base_url, args.allow_external_upload)
        elif args.action == "approve": result = approve(root, args.id)
        elif args.action == "link": result = link(root, args.from_id, args.relation, args.to_id, args.evidence)
        elif args.action == "validate": result = validate(root)
        elif args.action == "search":
            _, units, _ = store(root)
            result = [{"id": u["id"], "claim": u["claim"], "review": u["review"]} for u in units.values()
                      if not u["stale"] and args.keyword.lower() in u["claim"].lower()]
        elif args.action == "graph": result = graph(root, args.out)
        else: result = assemble(root, args.out, args.include_drafts)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.action == "validate" and not result["ok"] else 0

if __name__ == "__main__":
    sys.exit(main())
