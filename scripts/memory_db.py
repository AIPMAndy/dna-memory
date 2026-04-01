#!/usr/bin/env python3
"""DNA Memory 数据库兼容层。

历史脚本会从 ``scripts.memory_db`` 导入 ``get_db``，
而当前核心实现已经迁移到 ``scripts.evolve``。
该模块提供稳定的转发入口，避免旧脚本在运行时出现
``ModuleNotFoundError: No module named 'scripts.memory_db'``。
"""

try:
    # 作为包模块导入（例如 `python -m scripts.evolve` 场景）
    from scripts.evolve import get_db, init_db, DB_PATH  # type: ignore
except ModuleNotFoundError:
    # 作为顶层模块导入（例如脚本把 `scripts/` 加入 sys.path 后 `import memory_db`）
    from evolve import get_db, init_db, DB_PATH  # type: ignore

__all__ = ["get_db", "init_db", "DB_PATH"]
