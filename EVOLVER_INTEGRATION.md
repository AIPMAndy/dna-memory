# DNA Memory v3.0 - Evolver 整合方案
**日期：** 2026-04-17 23:50  
**目标：** 将 Evolver 的核心机制整合到 DNA Memory，实现协议驱动的记忆进化

---

## 核心整合点

### 1. 信号驱动选择器（Signal-Driven Selector）

**Evolver 机制**：
- 从 `memory/` 日志中提取 signals
- 根据 signals 自动匹配最佳 Gene/Capsule
- 输出协议约束的 GEP 提示词

**DNA Memory 整合**：
```python
# 新增 scripts/signal_extractor.py
class SignalExtractor:
    """从对话/日志中提取记忆信号"""
    
    SIGNAL_PATTERNS = {
        'correction': [
            r'不是.*?是',
            r'应该.*?而不是',
            r'错了.*?正确的是',
        ],
        'preference': [
            r'我(喜欢|偏好|希望|想要)',
            r'不要.*?',
            r'以后.*?',
        ],
        'decision': [
            r'决定.*?',
            r'选择.*?而不是',
            r'最终采用',
        ],
        'error': [
            r'失败.*?原因',
            r'错误.*?根因',
            r'踩坑',
        ],
        'workflow': [
            r'先.*?再.*?',
            r'流程.*?',
            r'步骤.*?',
        ],
    }
    
    def extract_signals(self, text):
        """提取信号并计算置信度"""
        signals = []
        for signal_type, patterns in self.SIGNAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    confidence = self._calculate_confidence(text, pattern)
                    signals.append({
                        'type': signal_type,
                        'content': text,
                        'confidence': confidence,
                        'pattern': pattern,
                    })
        return signals
    
    def _calculate_confidence(self, text, pattern):
        """计算置信度（基于上下文强度）"""
        base_confidence = 0.7
        
        # 强调词提升置信度
        emphasis_words = ['一定', '必须', '绝对', '永远', '记住']
        for word in emphasis_words:
            if word in text:
                base_confidence += 0.05
        
        # 否定词提升置信度
        if '不要' in text or '别' in text:
            base_confidence += 0.1
        
        return min(base_confidence, 0.98)
```

### 2. 进化策略预设（Evolution Strategy）

**Evolver 机制**：
- `balanced`: 50% 创新 + 30% 优化 + 20% 修复
- `innovate`: 80% 创新 + 15% 优化 + 5% 修复
- `harden`: 20% 创新 + 40% 优化 + 40% 修复
- `repair-only`: 0% 创新 + 20% 优化 + 80% 修复

**DNA Memory 整合**：
```python
# 新增 scripts/evolution_strategy.py
class EvolutionStrategy:
    """记忆进化策略"""
    
    STRATEGIES = {
        'balanced': {
            'new_memory_weight': 0.5,
            'reinforce_weight': 0.3,
            'decay_weight': 0.2,
        },
        'aggressive': {
            'new_memory_weight': 0.8,
            'reinforce_weight': 0.15,
            'decay_weight': 0.05,
        },
        'conservative': {
            'new_memory_weight': 0.2,
            'reinforce_weight': 0.4,
            'decay_weight': 0.4,
        },
        'cleanup': {
            'new_memory_weight': 0.0,
            'reinforce_weight': 0.2,
            'decay_weight': 0.8,
        },
    }
    
    def __init__(self, strategy='balanced'):
        self.strategy = self.STRATEGIES.get(strategy, self.STRATEGIES['balanced'])
    
    def should_remember(self, signal):
        """根据策略决定是否记录"""
        threshold = 1.0 - self.strategy['new_memory_weight']
        return signal['confidence'] >= threshold
    
    def should_reinforce(self, memory):
        """根据策略决定是否强化"""
        # 高频访问 + 策略权重
        return memory['access_count'] > 3 and random.random() < self.strategy['reinforce_weight']
    
    def should_decay(self, memory):
        """根据策略决定是否衰减"""
        # 长期未访问 + 策略权重
        days_since_access = (time.time() - memory['last_accessed']) / 86400
        return days_since_access > 7 and random.random() < self.strategy['decay_weight']
```

### 3. 信号去重（Signal Deduplication）

**Evolver 机制**：
- 检测修复循环（同一错误反复修复）
- 防止重复记录相同信号

**DNA Memory 整合**：
```python
# 增强 scripts/evolve.py 的 dedupe 功能
def detect_repair_loop(self):
    """检测修复循环"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 查找近期相似的 error 记忆
    cursor.execute("""
        SELECT id, content, created
        FROM memory
        WHERE type = 'error'
        AND created > ?
        ORDER BY created DESC
    """, (time.time() - 7 * 86400,))
    
    errors = cursor.fetchall()
    
    # 检测重复模式
    loops = []
    for i, error1 in enumerate(errors):
        for error2 in errors[i+1:]:
            similarity = self._calculate_similarity(error1[1], error2[1])
            if similarity > 0.85:
                loops.append({
                    'error1_id': error1[0],
                    'error2_id': error2[0],
                    'similarity': similarity,
                    'time_gap': error1[2] - error2[2],
                })
    
    conn.close()
    return loops

def prevent_duplicate_signal(self, signal):
    """防止重复信号"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 查找近期相似记忆
    cursor.execute("""
        SELECT id, content, weight
        FROM memory
        WHERE type = ?
        AND created > ?
    """, (signal['type'], time.time() - 3600))  # 1小时内
    
    recent = cursor.fetchall()
    
    for mem in recent:
        similarity = self._calculate_similarity(signal['content'], mem[1])
        if similarity > 0.9:
            # 重复信号，强化现有记忆而不是新建
            cursor.execute("""
                UPDATE memory
                SET weight = MIN(weight + 0.1, 1.0),
                    updated = ?
                WHERE id = ?
            """, (time.time(), mem[0]))
            conn.commit()
            conn.close()
            return False  # 不创建新记忆
    
    conn.close()
    return True  # 可以创建新记忆
```

### 4. GEP 协议资产体系（Gene/Capsule/Event）

**Evolver 机制**：
- **Gene**：单一进化模板（如"修复 API 超时"）
- **Capsule**：组合进化方案（如"API 稳定性加固"）
- **Event**：进化执行记录（可审计）

**DNA Memory 整合**：
```python
# 新增 scripts/gep_assets.py
class GEPAssets:
    """GEP 协议资产管理"""
    
    def __init__(self):
        self.genes_file = MEMORY_DIR / "genes.json"
        self.capsules_file = MEMORY_DIR / "capsules.json"
        self.events_file = MEMORY_DIR / "events.jsonl"
    
    def create_gene(self, name, description, triggers, actions):
        """创建 Gene（记忆模板）"""
        gene = {
            'id': f"gene_{int(time.time())}",
            'name': name,
            'description': description,
            'triggers': triggers,  # 触发条件
            'actions': actions,    # 执行动作
            'created': time.time(),
            'usage_count': 0,
        }
        
        genes = self._load_genes()
        genes.append(gene)
        self._save_genes(genes)
        
        return gene
    
    def create_capsule(self, name, gene_ids, strategy):
        """创建 Capsule（组合方案）"""
        capsule = {
            'id': f"capsule_{int(time.time())}",
            'name': name,
            'gene_ids': gene_ids,
            'strategy': strategy,
            'created': time.time(),
        }
        
        capsules = self._load_capsules()
        capsules.append(capsule)
        self._save_capsules(capsules)
        
        return capsule
    
    def record_event(self, event_type, details):
        """记录进化事件"""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details,
        }
        
        with open(self.events_file, 'a') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    def select_best_gene(self, signals):
        """根据信号选择最佳 Gene"""
        genes = self._load_genes()
        
        best_gene = None
        best_score = 0
        
        for gene in genes:
            score = self._calculate_gene_score(gene, signals)
            if score > best_score:
                best_score = score
                best_gene = gene
        
        return best_gene, best_score
    
    def _calculate_gene_score(self, gene, signals):
        """计算 Gene 匹配分数"""
        score = 0
        
        for signal in signals:
            for trigger in gene['triggers']:
                if trigger['type'] == signal['type']:
                    # 类型匹配
                    score += 0.3
                    
                    # 内容相似度
                    similarity = self._calculate_similarity(
                        trigger['pattern'],
                        signal['content']
                    )
                    score += similarity * 0.7
        
        # 归一化
        return score / len(signals) if signals else 0
```

### 5. Worker 池与分布式记忆（可选）

**Evolver 机制**：
- 节点加入 EvoMap 网络
- 接受分布式进化任务
- 共享 Gene/Capsule 资产

**DNA Memory 整合**：
```python
# 新增 scripts/memory_network.py
class MemoryNetwork:
    """分布式记忆网络"""
    
    def __init__(self, hub_url=None, node_id=None):
        self.hub_url = hub_url or os.getenv('MEMORY_HUB_URL')
        self.node_id = node_id or os.getenv('MEMORY_NODE_ID')
        self.enabled = bool(self.hub_url and self.node_id)
    
    def heartbeat(self):
        """向 Hub 发送心跳"""
        if not self.enabled:
            return
        
        stats = self._get_local_stats()
        
        try:
            response = requests.post(
                f"{self.hub_url}/heartbeat",
                json={
                    'node_id': self.node_id,
                    'stats': stats,
                    'capabilities': ['remember', 'recall', 'reflect'],
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                # 处理 Hub 返回的任务
                self._handle_tasks(data.get('tasks', []))
        except Exception as e:
            print(f"Heartbeat failed: {e}")
    
    def share_gene(self, gene):
        """分享 Gene 到网络"""
        if not self.enabled:
            return
        
        try:
            response = requests.post(
                f"{self.hub_url}/genes",
                json={
                    'node_id': self.node_id,
                    'gene': gene,
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Share gene failed: {e}")
            return False
    
    def fetch_gene(self, gene_id):
        """从网络获取 Gene"""
        if not self.enabled:
            return None
        
        try:
            response = requests.get(
                f"{self.hub_url}/genes/{gene_id}",
                params={'node_id': self.node_id},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fetch gene failed: {e}")
        
        return None
```

---

## 实施计划

### Phase 1: 核心整合（本周）

1. **信号提取器**
   - 实现 `scripts/signal_extractor.py`
   - 集成到 `memory_extractor.py`
   - 测试置信度计算

2. **进化策略**
   - 实现 `scripts/evolution_strategy.py`
   - 添加环境变量 `DNA_MEMORY_STRATEGY`
   - 更新 daemon 支持策略切换

3. **信号去重**
   - 增强 `dedupe` 功能
   - 实现修复循环检测
   - 添加重复信号防护

### Phase 2: GEP 资产体系（下周）

4. **GEP 资产管理**
   - 实现 `scripts/gep_assets.py`
   - 创建 `memory/genes.json`
   - 创建 `memory/capsules.json`
   - 创建 `memory/events.jsonl`

5. **Gene 选择器**
   - 实现信号 → Gene 匹配
   - 实现 Gene 评分算法
   - 集成到 reflect 流程

### Phase 3: 分布式网络（可选）

6. **记忆网络**
   - 实现 `scripts/memory_network.py`
   - 支持 Hub 心跳
   - 支持 Gene 共享

---

## 配置更新

### assets/config.json

```json
{
  "decay_days": 7,
  "decay_rate": 0.1,
  "forget_threshold": 0.2,
  "reflect_trigger": 20,
  "max_short_term": 100,
  "max_long_term": 500,
  "embedding_model": "text-embedding-3-small",
  "auto_reflect": true,
  "auto_reflect_interval_minutes": 30,
  "auto_decay": true,
  "auto_decay_interval_hours": 24,
  
  "evolution_strategy": "balanced",
  "signal_confidence_threshold": 0.7,
  "repair_loop_detection": true,
  "gep_enabled": true,
  
  "network": {
    "enabled": false,
    "hub_url": null,
    "node_id": null,
    "heartbeat_interval_minutes": 6
  }
}
```

---

## 预期效果

### 整合前
- 手动识别记忆类型
- 固定记忆策略
- 可能重复记录相同内容
- 无进化资产复用

### 整合后
- ✅ 自动信号提取 + 置信度评估
- ✅ 动态进化策略（balanced/aggressive/conservative/cleanup）
- ✅ 修复循环检测 + 重复信号防护
- ✅ GEP 资产体系（Gene/Capsule/Event）
- ✅ 可选分布式记忆网络

---

## 下一步行动

1. ✅ 创建整合方案文档
2. ⏳ 实现 signal_extractor.py
3. ⏳ 实现 evolution_strategy.py
4. ⏳ 增强 dedupe 功能
5. ⏳ 实现 gep_assets.py
6. ⏳ 更新 README.md
7. ⏳ 提交到 GitHub

---

**总结**：通过整合 Evolver 的核心机制，DNA Memory 将从"被动记录"升级为"主动进化"，实现协议驱动的记忆管理。
