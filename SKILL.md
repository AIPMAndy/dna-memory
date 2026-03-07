---
name: dna-memory
description: |
  DNA 记忆系统 - 让 AI Agent 像人脑一样学习和成长。
  三层记忆架构（工作/短期/长期）+ 主动遗忘 + 自动归纳 + 反思循环 + 记忆关联。
  激活场景：用户提到"记忆"、"学习"、"进化"、"成长"、"记住"、"回顾"、"反思"。
---

# DNA Memory - DNA 记忆系统

> 让 Agent 不只是记住，而是真正学会。

## 核心理念

人脑不是硬盘，不会无差别存储所有信息。人脑会：
- **遗忘**不重要的
- **强化**反复出现的
- **归纳**零散信息为模式
- **反思**过去的成功和失败

DNA Memory 模拟这个过程，让 Agent 真正"进化"。

---

## 三层记忆架构

```
┌─────────────────────────────────────────────────┐
│  工作记忆 (Working Memory)                       │
│  - 当前会话的临时信息                            │
│  - 会话结束后自动筛选                            │
│  - 文件：memory/working.json                     │
└─────────────────────────────────────────────────┘
                    ↓ 筛选
┌─────────────────────────────────────────────────┐
│  短期记忆 (Short-term Memory)                    │
│  - 近7天的重要信息                               │
│  - 带衰减权重，不访问会逐渐遗忘                  │
│  - 文件：memory/short_term.json                  │
└─────────────────────────────────────────────────┘
                    ↓ 巩固
┌─────────────────────────────────────────────────┐
│  长期记忆 (Long-term Memory)                     │
│  - 经过验证的持久知识                            │
│  - 归纳后的认知模式                              │
│  - 文件：memory/long_term.json + patterns.md     │
└─────────────────────────────────────────────────┘
```

---

## 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `fact` | 事实信息 | "Andy 的微信是 AIPMAndy" |
| `preference` | 用户偏好 | "Andy 喜欢简洁直接的回复" |
| `skill` | 学到的技能 | "飞书 API 限流时要分段请求" |
| `error` | 犯过的错误 | "不要用 rm，用 trash" |
| `pattern` | 归纳的模式 | "推送 GitHub 前先检查网络" |
| `insight` | 深层洞察 | "Andy 更看重效率而非完美" |

---

## 核心操作

### 1. 记录 (Remember)

```bash
python3 scripts/evolve.py remember \
  --type fact \
  --content "Andy 的 GitHub 账号是 AIPMAndy" \
  --source "用户告知" \
  --importance 0.8
```

### 2. 回忆 (Recall)

```bash
python3 scripts/evolve.py recall "GitHub 账号"
```

返回相关记忆，按相关度和重要性排序。

### 3. 反思 (Reflect)

```bash
python3 scripts/evolve.py reflect
```

触发反思循环：
1. 回顾近期记忆
2. 识别重复模式
3. 归纳成认知模式
4. 更新长期记忆

### 4. 遗忘 (Forget)

```bash
python3 scripts/evolve.py decay
```

执行遗忘机制：
- 7天未访问的短期记忆权重衰减
- 权重低于阈值的记忆被清理
- 重要记忆不会被遗忘

### 5. 关联 (Link)

```bash
python3 scripts/evolve.py link <memory_id_1> <memory_id_2> --relation "因果"
```

建立记忆之间的关联，形成知识图谱。

### 6. 压缩去重 (Compact)

```bash
python3 scripts/evolve.py compact
```

用于一次性清理长期记忆中的重复 pattern，自动补全旧数据缺失的 `signature/origin_type`，降低长期记忆污染。

建议场景：
- 发现长期记忆被重复模式占满
- daemon 曾长时间高频运行 reflect
- 升级到新版 dedupe 逻辑后首次维护

### 7. 后台常驻 (Daemon)

启动（后台）：
```bash
python3 scripts/dna_memory_daemon.py start
```

查看状态：
```bash
python3 scripts/dna_memory_daemon.py status
```

停止：
```bash
python3 scripts/dna_memory_daemon.py stop
```

默认读取 `assets/config.json` 的节流参数：
- `auto_reflect_interval_minutes`（默认 30 分钟）
- `auto_decay_interval_hours`（默认 24 小时）

并且仅在有新的 `remember` 写入后才执行 `reflect`，避免重复归纳同一批记忆。
日志写入 `/tmp/dna-memory-daemon.log`。

---

## 自动触发

### 会话开始时
1. 加载相关长期记忆
2. 检查是否有待反思的短期记忆

### 会话结束时
1. 从工作记忆筛选重要信息
2. 存入短期记忆
3. 如果短期记忆积累足够，触发反思

### 每日自动
1. 执行遗忘机制
2. 检查是否需要归纳新模式

默认节流：
- `auto_reflect_interval_minutes=30`：自动反思最短间隔 30 分钟，避免高频重复归纳。
- `auto_decay_interval_hours=24`：自动遗忘最短间隔 24 小时。

### 并发安全
- `evolve.py` 已内置跨进程文件锁，支持前台命令与后台守护同时运行。
- JSON 写入采用原子替换，降低中断/并发导致的数据损坏风险。

---

## 记忆强化规则

记忆的重要性会动态调整：

| 事件 | 权重变化 |
|------|----------|
| 被访问/使用 | +0.1 |
| 被用户确认正确 | +0.2 |
| 被用户纠正 | 标记为错误，创建新记忆 |
| 7天未访问 | -0.1 |
| 关联到其他记忆 | +0.05 |
| 被归纳为模式 | 升级为长期记忆 |

---

## 认知模式 (Patterns)

当多个记忆呈现相似规律时，自动归纳为模式：

```markdown
## Pattern: GitHub 推送策略

**触发条件**: 需要 push 到 GitHub 时

**学到的教训**:
1. 先检查网络连通性
2. 超时后等待重试，不要立即放弃
3. 如果持续失败，提供手动操作方案

**来源记忆**: [mem_001, mem_003, mem_007]

**验证次数**: 5
**最后验证**: 2026-03-01
```

---

## 与现有系统集成

### 与 MEMORY.md 的关系
- MEMORY.md 是人工维护的高层记忆
- DNA Memory 是自动化的细粒度记忆
- 重要的 Pattern 可以提升到 MEMORY.md

### 与 self-improving-agent 的关系
- self-improving-agent 记录错误和学习
- DNA Memory 在此基础上增加：归纳、遗忘、关联
- 可以导入 .learnings/ 中的内容

---

## 文件结构

```
~/.openclaw/workspace/memory/
├── working.json        # 工作记忆（当前会话）
├── short_term.json     # 短期记忆（7天内）
├── long_term.json      # 长期记忆（持久）
├── patterns.md         # 归纳的认知模式
├── graph.json          # 记忆关联图谱
└── meta.json           # 元数据（统计、配置）
```

---

## 使用示例

### 场景1：学习用户偏好

```
用户: "以后回复简洁点，别那么啰嗦"

Agent 内部操作:
1. remember --type preference --content "用户偏好简洁回复" --importance 0.9
2. 后续回复自动调整风格
```

### 场景2：从错误中学习

```
操作失败: "飞书 API 429 限流"

Agent 内部操作:
1. remember --type error --content "飞书 API 频繁调用会 429"
2. remember --type skill --content "飞书 API 要分段请求，间隔5秒"
3. link error_mem skill_mem --relation "解决方案"
```

### 场景3：自动归纳

```
反思发现:
- 记忆1: "GitHub push 超时"
- 记忆2: "GitHub clone 超时"  
- 记忆3: "GitHub fetch 超时"

归纳为 Pattern:
"网络访问 GitHub 不稳定，需要重试机制"
```

---

## 配置

```json
{
  "decay_days": 7,
  "decay_rate": 0.1,
  "forget_threshold": 0.2,
  "reflect_trigger": 20,
  "max_short_term": 100,
  "max_long_term": 500
}
```

---

## 与其他记忆系统的对比

| 特性 | memu | self-improving | **DNA Memory** |
|------|------|----------------|-------------------|
| 存储 | ✅ | ✅ | ✅ |
| 检索 | ✅ 向量 | ❌ | ✅ 向量+关联 |
| 分类 | ❌ | ✅ | ✅ 6种类型 |
| 遗忘 | ❌ | ❌ | ✅ 主动遗忘 |
| 归纳 | ❌ | ❌ | ✅ 自动归纳 |
| 反思 | ❌ | ❌ | ✅ 反思循环 |
| 关联 | ❌ | ❌ | ✅ 知识图谱 |
| 强化 | ❌ | ❌ | ✅ 动态权重 |

---

**Created by AI酋长Andy** | 让 Agent 真正学会成长
