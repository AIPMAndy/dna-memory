# 自动记忆采集器架构设计

## 设计目标

**零配置、零感知、高准确率**

用户无需手动 `remember`，系统在后台自动识别对话中值得记录的内容，静默采集。

---

## 核心原则

1. **高精准低召回**：宁可漏掉 30%，不能误采 10%（避免垃圾记忆污染）
2. **实时增量**：只分析新消息，不重复处理
3. **轻量优先**：先用规则引擎，准确率 > 80% 后再考虑 LLM
4. **用户可控**：提供反馈机制（点赞/删除）持续优化

---

## 架构分层

```
┌─────────────────────────────────────────┐
│  MCP Message Hook (mcp-server/hooks.py) │
│  监听 Claude Code 对话流                  │
└──────────────┬──────────────────────────┘
               │ notifications/messages/updated
               ↓
┌─────────────────────────────────────────┐
│  Auto Memory Collector                   │
│  (scripts/auto_memory_collector.py)      │
├─────────────────────────────────────────┤
│  1. 内容过滤器 (ContentFilter)            │
│     - 长度检查 (min 10 words)             │
│     - 噪音过滤 (感谢/问好/确认)            │
│  2. 规则引擎 (RuleEngine)                 │
│     - 偏好识别 (PreferenceDetector)       │
│     - 决策识别 (DecisionDetector)         │
│     - 错误识别 (ErrorDetector)            │
│     - 知识识别 (KnowledgeDetector)        │
│  3. 重要性评分 (ImportanceScorer)         │
│  4. 去重检查 (DeduplicateChecker)         │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  evolve.add_memory()                     │
│  写入 SQLite (自动分类 + 评分)            │
└─────────────────────────────────────────┘
```

---

## 规则引擎设计

### 1. 偏好识别 (PreferenceDetector)

**目标**：识别用户的编码风格、工具选择、工作习惯

**触发模式**：

| 模式 | 示例 | 重要性 |
|------|------|--------|
| `我喜欢/偏好 [对象]` | "我喜欢用 TypeScript" | 0.85 |
| `我习惯 [动作]` | "我习惯先写测试" | 0.80 |
| `我不喜欢/讨厌 [对象]` | "我讨厌过度抽象" | 0.85 |
| `我通常/一般 [动作]` | "我一般用 bun 而不是 npm" | 0.75 |
| `更喜欢 [A] 而不是 [B]` | "更喜欢 FastAPI 而不是 Flask" | 0.80 |

**实现**：
```python
class PreferenceDetector:
    PATTERNS = [
        (r'我(喜欢|偏好|更喜欢)(.+)', 0.85),
        (r'我(不喜欢|讨厌|不要)(.+)', 0.85),
        (r'我(习惯|通常|一般)(.+)', 0.75),
        (r'(更喜欢|prefer)\s*(.+?)\s*(而不是|over)\s*(.+)', 0.80),
    ]
    
    def detect(self, text: str) -> Optional[Memory]:
        for pattern, score in self.PATTERNS:
            if match := re.search(pattern, text, re.IGNORECASE):
                return Memory(
                    type='preference',
                    content=text.strip(),
                    importance=score,
                    extracted_entity=match.group(2).strip()
                )
        return None
```

---

### 2. 决策识别 (DecisionDetector)

**目标**：记录技术选型、架构决策

**触发模式**：

| 模式 | 示例 | 重要性 |
|------|------|--------|
| `决定/选择 [方案]` | "决定用 PostgreSQL 作为主库" | 0.90 |
| `使用/采用 [技术]` | "使用 Next.js 14 重构前端" | 0.85 |
| `改为/切换到 [方案]` | "切换到 Supabase" | 0.85 |
| `不用/放弃 [方案]，因为` | "不用 MongoDB，性能不够" | 0.80 |

**实现**：
```python
class DecisionDetector:
    PATTERNS = [
        (r'(决定|选择|确定)(用|使用|采用)?\s*(.+)', 0.90),
        (r'(使用|采用|引入)\s*(.+?)\s*(来|做|重构)', 0.85),
        (r'(改为|切换到|迁移到)\s*(.+)', 0.85),
        (r'(不用|放弃|废弃)\s*(.+?)[,，](因为|原因是)(.+)', 0.80),
    ]
```

---

### 3. 错误识别 (ErrorDetector)

**目标**：记录失败案例 + 解决方案（最有价值）

**触发模式**：

| 模式 | 示例 | 重要性 |
|------|------|--------|
| `[错误描述] + 解决方案` | "数据库锁定错误，修改为单一事务" | 0.95 |
| `踩坑：[问题]` | "踩坑：MCP SDK 需要 Python 3.10+" | 0.90 |
| `失败/报错：[问题]，[解决]` | "API 超时，加了重试机制" | 0.90 |
| `注意/警告：[经验]` | "注意：飞书 API 有频率限制" | 0.85 |

**实现**：
```python
class ErrorDetector:
    ERROR_KEYWORDS = ['错误', '报错', '失败', 'error', 'bug', '问题', '踩坑']
    SOLUTION_KEYWORDS = ['解决', '修复', '改为', 'fixed', 'solved', '方案']
    
    def detect(self, text: str) -> Optional[Memory]:
        has_error = any(kw in text.lower() for kw in self.ERROR_KEYWORDS)
        has_solution = any(kw in text.lower() for kw in self.SOLUTION_KEYWORDS)
        
        if has_error and has_solution:
            return Memory(
                type='error',
                content=text.strip(),
                importance=0.95  # 错误教训最有价值
            )
        elif has_error:
            return Memory(
                type='error',
                content=text.strip(),
                importance=0.80  # 仅有问题描述
            )
        return None
```

---

### 4. 知识识别 (KnowledgeDetector)

**目标**：记录新学到的知识点

**触发模式**：

| 模式 | 示例 | 重要性 |
|------|------|--------|
| `原来 [知识]` | "原来 React 18 支持并发渲染" | 0.75 |
| `发现 [知识]` | "发现 SQLite 支持 FTS5 全文搜索" | 0.75 |
| `了解到 [知识]` | "了解到 MCP 用 stdio 通信" | 0.70 |
| `[技术] 可以 [能力]` | "Next.js 可以做服务端渲染" | 0.70 |

**实现**：
```python
class KnowledgeDetector:
    PATTERNS = [
        (r'(原来|发现|了解到|才知道)(.+)', 0.75),
        (r'(.+?)(可以|能够|支持)(.+)', 0.70),
    ]
```

---

## 重要性评分算法

```python
class ImportanceScorer:
    def score(self, memory: Memory, context: dict) -> float:
        """
        多维度评分：
        1. 基础分（规则引擎给出）
        2. 长度加成（详细度）
        3. 实体密度（包含技术名词）
        4. 上下文相关性（与当前任务相关）
        """
        base_score = memory.importance
        
        # 长度加成（20-100 字最佳）
        length = len(memory.content)
        length_bonus = 0
        if 20 <= length <= 100:
            length_bonus = 0.05
        elif length > 100:
            length_bonus = 0.10  # 详细内容更有价值
        
        # 实体密度（识别技术名词）
        tech_entities = self._extract_tech_entities(memory.content)
        entity_bonus = min(len(tech_entities) * 0.02, 0.10)
        
        # 上下文相关性（如果与当前任务相关）
        context_bonus = 0
        if context.get('current_task'):
            if self._is_relevant(memory.content, context['current_task']):
                context_bonus = 0.10
        
        final_score = min(base_score + length_bonus + entity_bonus + context_bonus, 1.0)
        return final_score
    
    def _extract_tech_entities(self, text: str) -> list:
        """识别技术实体（简单版本）"""
        TECH_KEYWORDS = {
            'react', 'next.js', 'typescript', 'python', 'sqlite', 'postgresql',
            'api', 'mcp', 'github', 'git', 'docker', 'kubernetes', 'aws',
            'fastapi', 'flask', 'django', 'supabase', 'vercel'
        }
        return [kw for kw in TECH_KEYWORDS if kw in text.lower()]
```

---

## 内容过滤器

```python
class ContentFilter:
    MIN_LENGTH = 10  # 最少 10 个字符
    
    NOISE_PATTERNS = [
        r'^(好的|OK|知道了|明白|收到|谢谢|感谢)$',
        r'^(继续|下一步|开始吧)$',
        r'^(是的|对|没错|对的)$',
    ]
    
    def should_skip(self, text: str) -> bool:
        """判断是否应跳过"""
        # 太短
        if len(text.strip()) < self.MIN_LENGTH:
            return True
        
        # 纯噪音
        for pattern in self.NOISE_PATTERNS:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        
        # 纯代码块（不记录代码）
        if text.strip().startswith('```') and text.strip().endswith('```'):
            return True
        
        return False
```

---

## 去重检查

```python
class DeduplicateChecker:
    def is_duplicate(self, new_memory: Memory) -> bool:
        """
        检查是否已存在相似记忆：
        1. 精确匹配（content 完全相同）
        2. 模糊匹配（编辑距离 < 20%）
        3. 语义匹配（可选，Phase 2 引入 embedding）
        """
        # 查询最近 100 条同类型记忆
        recent_memories = evolve.recall(
            query=f"type:{new_memory.type}",
            limit=100
        )
        
        for existing in recent_memories:
            # 精确匹配
            if existing.content == new_memory.content:
                return True
            
            # 模糊匹配（编辑距离）
            similarity = self._edit_distance_similarity(
                existing.content,
                new_memory.content
            )
            if similarity > 0.80:  # 80% 相似度视为重复
                return True
        
        return False
    
    def _edit_distance_similarity(self, s1: str, s2: str) -> float:
        """计算编辑距离相似度"""
        import difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio()
```

---

## 工作流程

```
1. MCP Hook 接收新消息
   ↓
2. ContentFilter 过滤噪音
   ↓ (pass)
3. RuleEngine 并行运行 4 个 Detector
   ↓ (匹配到规则)
4. ImportanceScorer 评分
   ↓ (分数 > 0.6)
5. DeduplicateChecker 去重
   ↓ (非重复)
6. evolve.add_memory() 写入数据库
   ↓
7. 记录采集日志（用于后续优化）
```

---

## 性能指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| 准确率 | > 80% | 人工标注 100 条对话，计算 TP/(TP+FP) |
| 召回率 | > 60% | 人工标注 100 条对话，计算 TP/(TP+FN) |
| 响应时间 | < 50ms | 单条消息处理耗时 |
| 误采率 | < 10% | 用户删除比例 |

---

## Phase 1 简化版 vs Phase 2 完整版

| 功能 | Phase 1（Week 1-4） | Phase 2（Week 5+） |
|------|---------------------|-------------------|
| 内容过滤 | ✅ 规则匹配 | ✅ 规则匹配 |
| 偏好识别 | ✅ 正则表达式 | ✅ 正则 + NER |
| 决策识别 | ✅ 正则表达式 | ✅ 正则 + NER |
| 错误识别 | ✅ 关键词匹配 | ✅ 结构化提取 |
| 知识识别 | ✅ 正则表达式 | ✅ 正则 + NER |
| 重要性评分 | ✅ 规则评分 | ✅ 规则 + 上下文 |
| 去重检查 | ✅ 编辑距离 | ✅ 编辑距离 + Embedding |
| LLM 辅助 | ❌ 不使用 | ⚠️ 可选（低置信度时） |

**Phase 1 理念**：80% 准确率的规则引擎 > 95% 准确率但需要 API 调用的 LLM

---

## 用户反馈机制（Phase 1.5）

```python
# 新增 MCP Tool: dna_feedback
def handle_feedback(memory_id: int, action: str, reason: str = ""):
    """
    用户反馈：
    - action='upvote' → 权重 +0.1
    - action='downvote' → 权重 -0.2
    - action='delete' → 标记为误采（用于优化规则）
    """
    if action == 'delete':
        # 记录误采样本
        log_false_positive(memory_id, reason)
    
    evolve.update_memory_weight(memory_id, action)
```

---

## 下一步

✅ 架构设计完成  
⬜ 实现 `auto_memory_collector.py`（Week 1-2）  
⬜ 实现 `mcp-server/hooks.py`（Week 1-2）  
⬜ 准备测试数据集（标注 100 条对话）  
⬜ 准确率验证（Week 3）
