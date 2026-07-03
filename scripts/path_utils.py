#!/usr/bin/env python3
"""
路径工具 - 自动检测 DNA Memory 安装位置
"""
from pathlib import Path
import os

def get_dna_memory_root():
    """获取 DNA Memory 根目录（自动检测）"""
    # 方法1: 从当前脚本位置推导
    current_file = Path(__file__).resolve()
    if current_file.parent.name == 'scripts':
        return current_file.parent.parent
    
    # 方法2: 检查常见安装位置
    possible_locations = [
        Path.home() / ".cc-switch" / "skills" / "dna-memory",
        Path.home() / ".claude" / "skills" / "dna-memory",
        Path.home() / ".openclaw" / "skills" / "dna-memory",
    ]
    
    for loc in possible_locations:
        if loc.exists() and (loc / "memory").exists():
            return loc
    
    # 方法3: 环境变量
    env_path = os.getenv('DNA_MEMORY_ROOT')
    if env_path:
        return Path(env_path)
    
    # 默认返回 .cc-switch
    return Path.home() / ".cc-switch" / "skills" / "dna-memory"

def get_db_path():
    """获取数据库路径"""
    return get_dna_memory_root() / "memory" / "memory.db"

def get_working_memory_path():
    """获取工作记忆路径"""
    return get_dna_memory_root() / "memory" / "working.json"

def get_config_path():
    """获取配置文件路径"""
    return get_dna_memory_root() / "assets" / "config.json"

if __name__ == '__main__':
    print(f"DNA Memory 根目录: {get_dna_memory_root()}")
    print(f"数据库路径: {get_db_path()}")
    print(f"工作记忆: {get_working_memory_path()}")
    print(f"配置文件: {get_config_path()}")
