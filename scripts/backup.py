#!/usr/bin/env python3
"""
DNA Memory - 备份/恢复模块
支持 JSON 导出和 SQLite 文件备份
"""

import json
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.memory_db import get_db
import time

MEMORY_DIR = Path(__file__).parent.parent / "memory"
DB_PATH = MEMORY_DIR / "memory.db"
BACKUP_DIR = MEMORY_DIR / "backups"


# ============ JSON 导出/导入 ============
def export_all(output_path=None):
    """导出所有记忆"""
    conn = get_db()
    cursor = conn.cursor()

    # 导出 memory 表
    cursor.execute("SELECT * FROM memory")
    memories = cursor.fetchall()

    # 获取列名
    columns = [desc[0] for desc in cursor.description]

    data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "memories": [dict(zip(columns, row)) for row in memories]
    }

    # 导出关联
    cursor.execute("SELECT * FROM memory_relations")
    relations = cursor.fetchall()
    if relations:
        rel_columns = [desc[0] for desc in cursor.description]
        data["relations"] = [dict(zip(rel_columns, row)) for row in relations]

    conn.close()

    if not output_path:
        output_path = BACKUP_DIR / f"dna_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"✅ 导出完成: {output_path}")
    print(f"   记忆: {len(data['memories'])} 条")
    print(f"   关联: {len(data.get('relations', []))} 条")
    
    return data


def import_data(input_path, merge=True):
    """导入记忆"""
    data = json.loads(Path(input_path).read_text())
    
    conn = get_db()
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    
    for mem in data.get("memories", []):
        if merge:
            # 检查是否已存在
            cursor.execute("SELECT id FROM memory WHERE content = ?", (mem.get("content", ""),))
            if cursor.fetchone():
                skipped += 1
                continue
        
        cursor.execute("""
            INSERT INTO memory (content, type, tags, weight, short_term, long_term, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mem.get("content"),
            mem.get("type", "fact"),
            mem.get("tags", ""),
            mem.get("weight", 0.5),
            mem.get("short_term", 0),
            mem.get("long_term", 0),
            mem.get("created", time.time()),
            time.time()
        ))
        imported += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ 导入完成: {imported} 条新记忆")
    print(f"   跳过: {skipped} 条（已存在）")
    return {"imported": imported, "skipped": skipped}


# ============ SQLite 文件备份 ============
def create_db_backup(backup_dir: Path = BACKUP_DIR) -> Path:
    """创建数据库备份"""
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"数据库不存在: {DB_PATH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"memory_{timestamp}.db"

    shutil.copy(DB_PATH, backup_path)
    return backup_path


def cleanup_old_backups(backup_dir: Path = BACKUP_DIR, keep_days: int = 7):
    """清理旧备份"""
    if not backup_dir.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=keep_days)
    removed = 0

    for backup_file in backup_dir.glob("memory_*.db"):
        try:
            timestamp_str = backup_file.stem.split('_', 1)[1]
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            if file_time < cutoff_time:
                backup_file.unlink()
                removed += 1
        except Exception:
            pass

    return removed


def list_db_backups(backup_dir: Path = BACKUP_DIR):
    """列出所有数据库备份"""
    if not backup_dir.exists():
        return []

    backups = []
    for backup_file in sorted(backup_dir.glob("memory_*.db")):
        try:
            timestamp_str = backup_file.stem.split('_', 1)[1]
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            backups.append({
                'path': backup_file,
                'time': file_time,
                'size_mb': size_mb
            })
        except Exception:
            pass

    return backups


def restore_db_backup(backup_path: Path, confirm: bool = False):
    """恢复数据库备份"""
    if not backup_path.exists():
        raise FileNotFoundError(f"备份不存在: {backup_path}")

    if not confirm:
        print(f"⚠️  这将覆盖当前数据库: {DB_PATH}")
        response = input("确认恢复? (yes/no): ")
        if response.lower() != 'yes':
            print("已取消")
            return False

    shutil.copy(backup_path, DB_PATH)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DNA Memory 备份工具')
    subparsers = parser.add_subparsers(dest='action', help='操作')

    # export
    p_export = subparsers.add_parser('export', help='导出 JSON')
    p_export.add_argument('--path', help='输出路径')

    # import
    p_import = subparsers.add_parser('import', help='导入 JSON')
    p_import.add_argument('path', help='JSON 文件路径')
    p_import.add_argument('--merge', action='store_true', default=True, help='合并模式')

    # backup
    p_backup = subparsers.add_parser('backup', help='创建数据库备份')
    p_backup.add_argument('--keep-days', type=int, default=7, help='保留天数')

    # list
    subparsers.add_parser('list', help='列出数据库备份')

    # restore
    p_restore = subparsers.add_parser('restore', help='恢复数据库备份')
    p_restore.add_argument('backup_file', help='备份文件路径')
    p_restore.add_argument('--yes', action='store_true', help='跳过确认')

    # cleanup
    p_cleanup = subparsers.add_parser('cleanup', help='清理旧备份')
    p_cleanup.add_argument('--keep-days', type=int, default=7, help='保留天数')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(0)

    try:
        if args.action == 'export':
            export_all(args.path)

        elif args.action == 'import':
            import_data(args.path, merge=args.merge)

        elif args.action == 'backup':
            backup_path = create_db_backup()
            print(f"✅ 备份创建: {backup_path}")
            removed = cleanup_old_backups(keep_days=args.keep_days)
            if removed > 0:
                print(f"🗑️  清理 {removed} 个旧备份")

        elif args.action == 'list':
            backups = list_db_backups()
            if not backups:
                print("没有备份")
            else:
                print(f"📦 找到 {len(backups)} 个备份:\n")
                for b in backups:
                    print(f"  {b['time'].strftime('%Y-%m-%d %H:%M:%S')} | {b['size_mb']:.2f} MB")
                    print(f"    {b['path']}")

        elif args.action == 'restore':
            backup_path = Path(args.backup_file)
            if restore_db_backup(backup_path, confirm=args.yes):
                print(f"✅ 恢复完成: {backup_path}")

        elif args.action == 'cleanup':
            removed = cleanup_old_backups(keep_days=args.keep_days)
            print(f"🗑️  清理 {removed} 个旧备份 (保留 {args.keep_days} 天)")

    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
