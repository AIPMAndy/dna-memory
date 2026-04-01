# DNA Memory 项目可用性审查（2026-04-01）

> 审查目标：从“新用户 30 秒上手 + 日常开发者维护 + 生产安全运行”三个视角评估当前仓库可用性。

## 1) 审查范围与方法

- 代码与文档抽样：`README.md`、`SKILL.md`、`assets/config.json`、`scripts/*.py`。
- 命令行冒烟验证：`evolve.py` 核心路径、`cli.py` 兼容路径、静态编译检查。
- 重点关注：安装成本、命令一致性、故障可诊断性、默认配置安全性、向后兼容。

## 2) 结论（TL;DR）

项目核心路径（`scripts/evolve.py`）可用、体验顺滑，且“本地优先 + SQLite + FTS 回退”设计对个人 Agent 场景友好。

但存在**中高优先级可用性问题**：多个辅助脚本依赖了已缺失模块 `scripts.memory_db`，导致运行即报错，破坏 README 中“可直接使用”的用户预期。该问题已通过新增兼容层 `scripts/memory_db.py` 修复。

## 3) 详细发现

### A. 首次体验（Onboarding）

**优点**
- README 的价值主张清晰，功能定位与同类对比直观。
- “30 秒快速开始”命令可直接跑通（remember/recall/stats）。

**问题**
- 文档展示的“真实架构”包含较多脚本，用户会自然尝试 `cli.py` / `api.py` / `backup.py` 等命令；在本次修复前，这些入口会因为缺失 `scripts.memory_db` 直接失败。

### B. 命令与接口一致性

**优点**
- `evolve.py --help` 设计完整，命令结构统一。
- recall 支持 `type:xxx` 与多关键词 AND，易理解。

**问题**
- 子模块在数据库访问层不一致：
  - 核心走 `evolve.get_db()`；
  - 辅助脚本走 `memory_db.get_db()`（缺失）。
- 这属于“接口演进后兼容层缺位”典型问题。

### C. 运行稳定性与可诊断性

**优点**
- daemon 有 PID、日志、interval 配置；reflect 支持“无新增记忆则跳过”，节省开销。
- 多数核心逻辑有 fallback（如 FTS5 -> LIKE）。

**问题（建议）**
- 多处 `except: pass` 虽可提升健壮性，但排障信息不足；建议至少在 debug 模式输出错误原因。
- `semantic_search.py` 默认依赖 `numpy`，而项目无依赖声明文件（requirements/pyproject），会让用户在语义检索时遇到“隐性安装门槛”。

### D. 配置与默认值

**优点**
- `assets/config.json` 提供自动 reflect/decay 节流参数，默认值合理。

**风险（建议）**
- `embedding_model` 默认 OpenAI 模型，但 README 强调“零重依赖核心”；建议文档明确：语义检索是可选增强，并附离线 fallback 说明位置。

## 4) 已执行修复

- 新增 `scripts/memory_db.py` 兼容模块，统一转发到 `scripts.evolve`，恢复旧入口脚本可用性。

## 5) 优先级建议（接下来 1~2 个迭代）

1. **P0**：补充依赖说明（至少 README 增加 optional deps 小节：`numpy`, `requests`）。
2. **P1**：提供 `requirements.txt` 或 `pyproject.toml`，降低“脚本可运行但环境不可复现”的风险。
3. **P1**：为 `api.py` / `backup.py` / `semantic_search.py` 增加最小冒烟测试。
4. **P2**：统一异常处理策略（`--debug` 时打印 traceback，默认友好提示）。
5. **P2**：将“核心路径”和“实验路径”在 README 中分层标注，减少新用户认知负担。

## 6) 可用性评分（主观量化）

- 核心功能可用性：**8.5/10**
- 辅助功能可用性：**6.5/10**（本次兼容修复后可提升到 **7.5/10**）
- 文档可执行一致性：**7/10**
- 维护友好度：**7/10**

**综合：7.5/10（当前）**，具备较强实用价值，建议按上方优先级进行产品化打磨。
