#!/usr/bin/env python3
"""
DNA Memory - 进化式记忆系统

让 AI Agent 像人脑一样学习和成长：
- 三层记忆架构（工作/短期/长期）
- 主动遗忘机制
- 自动归纳模式
- 反思循环
- 知识图谱关联
"""

import json
import os
import tempfile
import time
import uuid
import argparse
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

# 路径配置
SKILL_DIR = Path(__file__).parent.parent
MEMORY_DIR = Path(os.environ.get("DNA_MEMORY_DIR", str(Path.home() / ".openclaw" / "workspace" / "memory"))).expanduser()
CONFIG_FILE = SKILL_DIR / "assets" / "config.json"

SHORT_TERM_FILE = MEMORY_DIR / "short_term.json"
LONG_TERM_FILE = MEMORY_DIR / "long_term.json"
PATTERNS_FILE = MEMORY_DIR / "patterns.md"
GRAPH_FILE = MEMORY_DIR / "graph.json"
META_FILE = MEMORY_DIR / "meta.json"
LOCK_FILE = MEMORY_DIR / ".dna-memory.lock"

MEMORY_TYPES = ["fact", "preference", "skill", "error", "pattern", "insight"]

# 默认配置
DEFAULT_CONFIG = {
    "decay_days": 7,
    "decay_rate": 0.1,
    "forget_threshold": 0.2,
    "reflect_trigger": 20,
    "max_short_term": 100,
    "max_long_term": 500,
    "auto_reflect": True,
    "auto_reflect_interval_minutes": 30,
    "auto_decay": True,
    "auto_decay_interval_hours": 24
}


def load_config() -> Dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
        except:
            pass
    return DEFAULT_CONFIG


def ensure_dirs():
    """确保目录存在"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def memory_lock(timeout: float = 10.0, poll_interval: float = 0.05):
    """跨进程文件锁，避免前后台并发写坏 JSON"""
    ensure_dirs()
    lock_handle = open(LOCK_FILE, "a+", encoding="utf-8")

    if fcntl is None:
        try:
            yield
        finally:
            lock_handle.close()
        return

    start = time.monotonic()
    while True:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() - start >= timeout:
                lock_handle.close()
                raise TimeoutError("DNA memory lock timeout")
            time.sleep(poll_interval)

    try:
        yield
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def load_json(path: Path) -> Dict:
    """加载 JSON 文件"""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            return {"memories": []}
    return {"memories": []}


def save_json(path: Path, data: Dict):
    """原子保存 JSON 文件"""
    ensure_dirs()
    fd, temp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def gen_id() -> str:
    """生成唯一 ID"""
    return f"mem_{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    """获取当前 ISO 时间"""
    return datetime.now().isoformat()


def pattern_signature(memory_type: str, source_ids) -> str:
    """为模式生成稳定签名，避免重复归纳同一批来源记忆"""
    normalized_sources = sorted(str(sid) for sid in source_ids)
    return f"{memory_type}:{'|'.join(normalized_sources)}"


def update_meta(action: str, count: int = 1, extra: Optional[Dict] = None):
    """更新元数据统计"""
    meta = load_json(META_FILE)
    if "stats" not in meta:
        meta["stats"] = {}
    if action not in meta["stats"]:
        meta["stats"][action] = 0
    meta["stats"][action] += count
    meta["last_action"] = action
    meta["last_updated"] = now_iso()
    if extra:
        meta.update(extra)
    save_json(META_FILE, meta)


def should_run_auto_decay(config: Dict) -> bool:
    """判断是否应触发自动衰减"""
    if not config.get("auto_decay", True):
        return False

    interval_hours = float(config.get("auto_decay_interval_hours", 24))
    if interval_hours <= 0:
        return True

    meta = load_json(META_FILE)
    last_decay_at = meta.get("last_decay_at")
    if not last_decay_at:
        return True

    try:
        last = datetime.fromisoformat(last_decay_at)
        return (datetime.now() - last).total_seconds() >= interval_hours * 3600
    except Exception:
        return True


def should_run_auto_reflect(config: Dict) -> bool:
    """判断是否应触发自动反思"""
    if not config.get("auto_reflect", True):
        return False

    interval_minutes = float(config.get("auto_reflect_interval_minutes", 30))
    if interval_minutes <= 0:
        return True

    meta = load_json(META_FILE)
    last_reflect_at = meta.get("last_reflect_at")
    if not last_reflect_at:
        return True

    try:
        last = datetime.fromisoformat(last_reflect_at)
        return (datetime.now() - last).total_seconds() >= interval_minutes * 60
    except Exception:
        return True


def check_auto_actions(config: Dict):
    """检查是否需要自动执行反思或遗忘"""
    if should_run_auto_decay(config):
        print("🧹 自动触发遗忘...")
        _do_decay(config)

    if config.get("auto_reflect"):
        st = load_json(SHORT_TERM_FILE)
        if len(st.get("memories", [])) >= config.get("reflect_trigger", 20) and should_run_auto_reflect(config):
            print("💭 自动触发反思...")
            _do_reflect(config)


def cmd_remember(args):
    """记录新记忆"""
    config = load_config()
    
    memory = {
        "id": gen_id(),
        "type": args.type,
        "content": args.content,
        "source": getattr(args, 'source', 'user'),
        "importance": min(max(args.importance, 0), 1),
        "created_at": now_iso(),
        "last_accessed": now_iso(),
        "access_count": 0,
        "tags": getattr(args, 'tags', '').split(',') if getattr(args, 'tags', '') else [],
        "links": []
    }
    
    data = load_json(SHORT_TERM_FILE)
    
    # 检查是否超过上限
    if len(data.get("memories", [])) >= config.get("max_short_term", 100):
        # 移除最旧的低权重记忆
        data["memories"].sort(key=lambda x: (x["importance"], x["last_accessed"]))
        data["memories"] = data["memories"][1:]
    
    data["memories"].append(memory)
    save_json(SHORT_TERM_FILE, data)
    update_meta("remember")
    
    print(f"✅ 已记录: [{memory['id']}] {args.content[:50]}...")
    
    # 检查自动操作
    check_auto_actions(config)


def cmd_recall(args):
    """回忆相关记忆"""
    results = []
    query = args.query.lower()
    
    for file in [SHORT_TERM_FILE, LONG_TERM_FILE]:
        data = load_json(file)
        touched = False
        for mem in data.get("memories", []):
            content = mem.get("content", "").lower()
            tags = " ".join(mem.get("tags", [])).lower()
            
            if query in content or query in tags:
                # 更新访问信息
                mem["last_accessed"] = now_iso()
                mem["access_count"] = mem.get("access_count", 0) + 1
                mem["importance"] = min(mem.get("importance", 0.5) + 0.1, 1.0)
                results.append((mem, file))
                touched = True
        if touched:
            save_json(file, data)
    
    # 按重要性排序
    results.sort(key=lambda x: x[0].get("importance", 0), reverse=True)
    
    if not results:
        print(f"🔍 未找到与 '{args.query}' 相关的记忆")
        return
    
    update_meta("recall")
    
    for mem, source in results[:args.limit]:
        source_tag = "短期" if "short" in str(source) else "长期"
        importance = mem.get("importance", 0)
        print(f"[{mem['id']}] ({mem['type']}) [{source_tag}] {mem['content'][:60]}... [{importance:.2f}]")


def _do_reflect(config: Dict):
    """执行反思归纳逻辑"""
    data = load_json(SHORT_TERM_FILE)
    memories = data.get("memories", [])
    meta = load_json(META_FILE)
    remember_count = int(meta.get("stats", {}).get("remember", 0))
    
    if len(memories) < 3:
        print("📝 记忆不足，暂不归纳")
        update_meta("reflect", 0, {"last_reflect_at": now_iso(), "last_reflect_remember_count": remember_count})
        return 0
    
    # 按类型分组
    by_type = {}
    for mem in memories:
        t = mem.get("type", "fact")
        by_type.setdefault(t, []).append(mem)
    
    lt = load_json(LONG_TERM_FILE)
    lt_memories = lt.get("memories", [])
    existing_pattern_signatures = set()
    existing_ids = set()
    for mem in lt_memories:
        mem_id = mem.get("id")
        if mem_id:
            existing_ids.add(mem_id)
        if mem.get("type") == "pattern":
            signature = mem.get("signature")
            if not signature and mem.get("sources"):
                signature = pattern_signature(mem.get("origin_type", "pattern"), mem.get("sources", []))
            if signature:
                existing_pattern_signatures.add(signature)

    patterns = []
    promoted = []
    
    for t, mems in by_type.items():
        if len(mems) >= 3:
            # 提取共同主题
            contents = [m["content"] for m in mems]
            common_words = set(contents[0].split())
            for c in contents[1:]:
                common_words &= set(c.split())
            
            theme = " ".join(list(common_words)[:5]) if common_words else t
            
            sources = [m["id"] for m in mems]
            signature = pattern_signature(t, sources)
            if signature in existing_pattern_signatures:
                continue

            pattern = {
                "id": gen_id(),
                "type": "pattern",
                "content": f"[{t}类模式] {theme}: 归纳自 {len(mems)} 条记忆",
                "sources": sources,
                "signature": signature,
                "origin_type": t,
                "created_at": now_iso(),
                "last_accessed": now_iso(),
                "access_count": 0,
                "importance": 0.8,
                "tags": [t, "pattern"],
                "links": []
            }
            patterns.append(pattern)
            existing_pattern_signatures.add(signature)
            
            # 高权重记忆升级到长期
            for m in mems:
                if m.get("importance", 0) >= 0.7:
                    promoted.append(m)
    
    lt_memories.extend(patterns)

    # 升级高权重记忆（仅统计实际新增）
    promoted_added = 0
    for m in promoted:
        mem_id = m.get("id")
        if mem_id and mem_id not in existing_ids:
            lt_memories.append(m)
            existing_ids.add(mem_id)
            promoted_added += 1

    # 检查长期记忆上限
    max_lt = config.get("max_long_term", 500)
    if len(lt_memories) > max_lt:
        lt_memories.sort(key=lambda x: x.get("importance", 0))
        lt_memories = lt_memories[-max_lt:]

    if patterns or promoted_added:
        lt["memories"] = lt_memories
        save_json(LONG_TERM_FILE, lt)
        print(f"💡 归纳出 {len(patterns)} 个新模式，升级 {promoted_added} 条到长期记忆")
    else:
        print("📝 暂未发现新模式")

    update_meta(
        "reflect",
        len(patterns),
        {
            "last_reflect_at": now_iso(),
            "last_reflect_remember_count": remember_count,
        },
    )
    return len(patterns)


def cmd_reflect(args):
    """反思归纳"""
    config = load_config()
    _do_reflect(config)


def cmd_decay(args):
    """遗忘衰减"""
    config = load_config()
    _do_decay(config)


def _do_decay(config: Dict) -> int:
    """执行遗忘衰减并返回遗忘数量"""
    data = load_json(SHORT_TERM_FILE)
    now = datetime.now()
    kept, forgotten = [], []
    
    decay_days = config.get("decay_days", 7)
    decay_rate = config.get("decay_rate", 0.1)
    threshold = config.get("forget_threshold", 0.2)
    
    for mem in data.get("memories", []):
        try:
            last = datetime.fromisoformat(mem.get("last_accessed", mem.get("created_at", now_iso())))
            days = (now - last).days
            
            if days >= decay_days:
                mem["importance"] = mem.get("importance", 0.5) - decay_rate
                if mem["importance"] < threshold:
                    forgotten.append(mem)
                    continue
            kept.append(mem)
        except:
            kept.append(mem)
    
    data["memories"] = kept
    save_json(SHORT_TERM_FILE, data)
    update_meta("decay", len(forgotten), {"last_decay_at": now_iso()})
    print(f"🧹 遗忘 {len(forgotten)} 条，保留 {len(kept)} 条")
    return len(forgotten)


def cmd_link(args):
    """建立关联"""
    graph = load_json(GRAPH_FILE)
    if "links" not in graph:
        graph["links"] = []
    
    # 检查是否已存在
    for link in graph["links"]:
        if link["from"] == args.id1 and link["to"] == args.id2:
            print(f"⚠️ 关联已存在")
            return
    
    graph["links"].append({
        "from": args.id1,
        "to": args.id2,
        "relation": args.relation,
        "created_at": now_iso()
    })
    save_json(GRAPH_FILE, graph)
    update_meta("link")
    print(f"🔗 已关联: {args.id1} --[{args.relation}]--> {args.id2}")


def cmd_stats(args):
    """统计信息"""
    st = load_json(SHORT_TERM_FILE)
    lt = load_json(LONG_TERM_FILE)
    graph = load_json(GRAPH_FILE)
    meta = load_json(META_FILE)
    
    st_count = len(st.get("memories", []))
    lt_count = len(lt.get("memories", []))
    link_count = len(graph.get("links", []))
    
    print("📊 DNA Memory 统计")
    print(f"   短期记忆: {st_count} 条")
    print(f"   长期记忆: {lt_count} 条")
    print(f"   记忆关联: {link_count} 条")
    
    if meta.get("stats"):
        print("\n📈 操作统计")
        for k, v in meta["stats"].items():
            print(f"   {k}: {v} 次")
    
    if meta.get("last_updated"):
        print(f"\n🕐 最后更新: {meta['last_updated'][:19]}")


def cmd_list(args):
    """列出记忆"""
    file = LONG_TERM_FILE if args.long_term else SHORT_TERM_FILE
    data = load_json(file)
    memories = data.get("memories", [])
    
    if args.type:
        memories = [m for m in memories if m.get("type") == args.type]
    
    # 按重要性排序
    memories.sort(key=lambda x: x.get("importance", 0), reverse=True)
    
    source = "长期" if args.long_term else "短期"
    print(f"📋 {source}记忆列表 ({len(memories)} 条)")
    
    for mem in memories[:args.limit]:
        importance = mem.get("importance", 0)
        print(f"  [{mem['id']}] ({mem['type']}) {mem['content'][:50]}... [{importance:.2f}]")


def cmd_delete(args):
    """删除记忆"""
    deleted = False
    
    for file in [SHORT_TERM_FILE, LONG_TERM_FILE]:
        data = load_json(file)
        original_count = len(data.get("memories", []))
        data["memories"] = [m for m in data.get("memories", []) if m["id"] != args.id]
        
        if len(data["memories"]) < original_count:
            save_json(file, data)
            deleted = True
            print(f"🗑️ 已删除: {args.id}")
            break
    
    if not deleted:
        print(f"⚠️ 未找到: {args.id}")


def cmd_export(args):
    """导出记忆"""
    export_data = {
        "exported_at": now_iso(),
        "short_term": load_json(SHORT_TERM_FILE),
        "long_term": load_json(LONG_TERM_FILE),
        "graph": load_json(GRAPH_FILE)
    }
    
    output = args.output or f"dna_memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"📤 已导出到: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="DNA Memory - 进化式记忆系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s remember "Andy喜欢简洁回复" -t preference -i 0.9
  %(prog)s recall "Andy"
  %(prog)s reflect
  %(prog)s decay
  %(prog)s stats
        """
    )
    sub = parser.add_subparsers(dest="cmd", help="可用命令")
    
    # remember
    p = sub.add_parser("remember", help="记录新记忆")
    p.add_argument("content", help="记忆内容")
    p.add_argument("--type", "-t", default="fact", choices=MEMORY_TYPES, help="记忆类型")
    p.add_argument("--source", "-s", default="user", help="来源")
    p.add_argument("--importance", "-i", type=float, default=0.5, help="重要性 (0-1)")
    p.add_argument("--tags", help="标签，逗号分隔")
    p.set_defaults(func=cmd_remember)
    
    # recall
    p = sub.add_parser("recall", help="回忆相关记忆")
    p.add_argument("query", help="查询关键词")
    p.add_argument("--limit", "-l", type=int, default=5, help="返回数量上限")
    p.set_defaults(func=cmd_recall)
    
    # reflect
    p = sub.add_parser("reflect", help="反思归纳")
    p.set_defaults(func=cmd_reflect)
    
    # decay
    p = sub.add_parser("decay", help="遗忘衰减")
    p.set_defaults(func=cmd_decay)
    
    # link
    p = sub.add_parser("link", help="建立记忆关联")
    p.add_argument("id1", help="记忆 ID 1")
    p.add_argument("id2", help="记忆 ID 2")
    p.add_argument("--relation", "-r", default="related", help="关联类型")
    p.set_defaults(func=cmd_link)
    
    # stats
    p = sub.add_parser("stats", help="查看统计")
    p.set_defaults(func=cmd_stats)
    
    # list
    p = sub.add_parser("list", help="列出记忆")
    p.add_argument("--type", "-t", choices=MEMORY_TYPES, help="按类型过滤")
    p.add_argument("--long-term", "-L", action="store_true", help="列出长期记忆")
    p.add_argument("--limit", "-l", type=int, default=10, help="返回数量上限")
    p.set_defaults(func=cmd_list)
    
    # delete
    p = sub.add_parser("delete", help="删除记忆")
    p.add_argument("id", help="记忆 ID")
    p.set_defaults(func=cmd_delete)
    
    # export
    p = sub.add_parser("export", help="导出记忆")
    p.add_argument("--output", "-o", help="输出文件名")
    p.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        with memory_lock():
            args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
