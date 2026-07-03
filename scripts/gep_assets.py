#!/usr/bin/env python3
"""
GEP 资产管理 - Gene/Capsule/Event 体系
整合自 Evolver 的 GEP 协议
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class GEPAssets:
    """GEP 协议资产管理"""
    
    def __init__(self, memory_dir: Path = None):
        """
        初始化 GEP 资产管理
        
        Args:
            memory_dir: 记忆目录路径
        """
        if memory_dir is None:
            memory_dir = Path(__file__).parent.parent / "memory"
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.genes_file = self.memory_dir / "genes.json"
        self.capsules_file = self.memory_dir / "capsules.json"
        self.events_file = self.memory_dir / "events.jsonl"
        
        # 初始化文件
        self._init_files()
    
    def _init_files(self):
        """初始化资产文件"""
        if not self.genes_file.exists():
            self._save_genes([])
        
        if not self.capsules_file.exists():
            self._save_capsules([])
        
        if not self.events_file.exists():
            self.events_file.touch()
    
    # ============ Gene 管理 ============
    
    def create_gene(
        self,
        name: str,
        description: str,
        triggers: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        创建 Gene（记忆模板）
        
        Args:
            name: Gene 名称
            description: 描述
            triggers: 触发条件列表
            actions: 执行动作列表
            tags: 标签列表
        
        Returns:
            创建的 Gene
        """
        gene = {
            'id': f"gene_{int(time.time() * 1000)}",
            'name': name,
            'description': description,
            'triggers': triggers,
            'actions': actions,
            'tags': tags or [],
            'created': time.time(),
            'updated': time.time(),
            'usage_count': 0,
            'success_count': 0,
            'failure_count': 0,
        }
        
        genes = self._load_genes()
        genes.append(gene)
        self._save_genes(genes)
        
        # 记录事件
        self.record_event('gene_created', {
            'gene_id': gene['id'],
            'name': name,
        })
        
        return gene
    
    def get_gene(self, gene_id: str) -> Optional[Dict[str, Any]]:
        """获取 Gene"""
        genes = self._load_genes()
        for gene in genes:
            if gene['id'] == gene_id:
                return gene
        return None
    
    def list_genes(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        列出 Genes
        
        Args:
            tags: 标签过滤（可选）
        
        Returns:
            Gene 列表
        """
        genes = self._load_genes()
        
        if tags:
            genes = [
                g for g in genes
                if any(tag in g.get('tags', []) for tag in tags)
            ]
        
        return genes
    
    def update_gene_usage(self, gene_id: str, success: bool = True):
        """
        更新 Gene 使用统计
        
        Args:
            gene_id: Gene ID
            success: 是否成功
        """
        genes = self._load_genes()
        
        for gene in genes:
            if gene['id'] == gene_id:
                gene['usage_count'] += 1
                if success:
                    gene['success_count'] += 1
                else:
                    gene['failure_count'] += 1
                gene['updated'] = time.time()
                break
        
        self._save_genes(genes)
    
    def select_best_gene(self, signals: List[Dict[str, Any]]) -> Optional[tuple]:
        """
        根据信号选择最佳 Gene
        
        Args:
            signals: 信号列表
        
        Returns:
            (gene, score) 或 None
        """
        genes = self._load_genes()
        
        if not genes or not signals:
            return None
        
        best_gene = None
        best_score = 0
        
        for gene in genes:
            score = self._calculate_gene_score(gene, signals)
            if score > best_score:
                best_score = score
                best_gene = gene
        
        if best_score > 0.5:  # 最低匹配阈值
            return (best_gene, best_score)
        
        return None
    
    def _calculate_gene_score(
        self,
        gene: Dict[str, Any],
        signals: List[Dict[str, Any]]
    ) -> float:
        """
        计算 Gene 匹配分数
        
        Args:
            gene: Gene 字典
            signals: 信号列表
        
        Returns:
            匹配分数（0-1）
        """
        if not signals:
            return 0.0
        
        total_score = 0
        
        for signal in signals:
            for trigger in gene.get('triggers', []):
                # 类型匹配
                if trigger.get('type') == signal.get('type'):
                    total_score += 0.3
                    
                    # 关键词匹配
                    keywords = trigger.get('keywords', [])
                    content = signal.get('content', '').lower()
                    
                    matched_keywords = sum(
                        1 for kw in keywords if kw.lower() in content
                    )
                    
                    if keywords:
                        keyword_score = matched_keywords / len(keywords)
                        total_score += keyword_score * 0.7
        
        # 归一化
        max_possible_score = len(signals) * len(gene.get('triggers', []))
        if max_possible_score > 0:
            return min(total_score / max_possible_score, 1.0)
        
        return 0.0
    
    # ============ Capsule 管理 ============
    
    def create_capsule(
        self,
        name: str,
        description: str,
        gene_ids: List[str],
        strategy: str = 'sequential'
    ) -> Dict[str, Any]:
        """
        创建 Capsule（组合方案）
        
        Args:
            name: Capsule 名称
            description: 描述
            gene_ids: Gene ID 列表
            strategy: 执行策略（sequential/parallel）
        
        Returns:
            创建的 Capsule
        """
        capsule = {
            'id': f"capsule_{int(time.time() * 1000)}",
            'name': name,
            'description': description,
            'gene_ids': gene_ids,
            'strategy': strategy,
            'created': time.time(),
            'updated': time.time(),
            'usage_count': 0,
        }
        
        capsules = self._load_capsules()
        capsules.append(capsule)
        self._save_capsules(capsules)
        
        # 记录事件
        self.record_event('capsule_created', {
            'capsule_id': capsule['id'],
            'name': name,
            'gene_count': len(gene_ids),
        })
        
        return capsule
    
    def get_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        """获取 Capsule"""
        capsules = self._load_capsules()
        for capsule in capsules:
            if capsule['id'] == capsule_id:
                return capsule
        return None
    
    def list_capsules(self) -> List[Dict[str, Any]]:
        """列出所有 Capsules"""
        return self._load_capsules()
    
    # ============ Event 管理 ============
    
    def record_event(self, event_type: str, details: Dict[str, Any]):
        """
        记录进化事件
        
        Args:
            event_type: 事件类型
            details: 事件详情
        """
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details,
        }
        
        with open(self.events_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    def get_events(
        self,
        event_type: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取事件列表
        
        Args:
            event_type: 事件类型过滤（可选）
            limit: 返回数量限制
        
        Returns:
            事件列表
        """
        if not self.events_file.exists():
            return []
        
        events = []
        
        with open(self.events_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event_type is None or event.get('type') == event_type:
                        events.append(event)
                except json.JSONDecodeError:
                    continue
        
        # 按时间倒序
        events.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return events[:limit]
    
    # ============ 内部方法 ============
    
    def _load_genes(self) -> List[Dict[str, Any]]:
        """加载 Genes"""
        if not self.genes_file.exists():
            return []
        
        with open(self.genes_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_genes(self, genes: List[Dict[str, Any]]):
        """保存 Genes"""
        with open(self.genes_file, 'w', encoding='utf-8') as f:
            json.dump(genes, f, ensure_ascii=False, indent=2)
    
    def _load_capsules(self) -> List[Dict[str, Any]]:
        """加载 Capsules"""
        if not self.capsules_file.exists():
            return []
        
        with open(self.capsules_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_capsules(self, capsules: List[Dict[str, Any]]):
        """保存 Capsules"""
        with open(self.capsules_file, 'w', encoding='utf-8') as f:
            json.dump(capsules, f, ensure_ascii=False, indent=2)
    
    # ============ 统计 ============
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        genes = self._load_genes()
        capsules = self._load_capsules()
        events = self.get_events(limit=1000)
        
        return {
            'genes': {
                'total': len(genes),
                'total_usage': sum(g.get('usage_count', 0) for g in genes),
                'success_rate': self._calculate_success_rate(genes),
            },
            'capsules': {
                'total': len(capsules),
                'total_usage': sum(c.get('usage_count', 0) for c in capsules),
            },
            'events': {
                'total': len(events),
                'recent_24h': len([
                    e for e in events
                    if e.get('timestamp', 0) > time.time() - 86400
                ]),
            }
        }
    
    def _calculate_success_rate(self, genes: List[Dict[str, Any]]) -> float:
        """计算成功率"""
        total_success = sum(g.get('success_count', 0) for g in genes)
        total_failure = sum(g.get('failure_count', 0) for g in genes)
        total = total_success + total_failure
        
        if total == 0:
            return 0.0
        
        return total_success / total


# ============ CLI ============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='GEP 资产管理')
    parser.add_argument('--create-gene', action='store_true', help='创建 Gene')
    parser.add_argument('--list-genes', action='store_true', help='列出 Genes')
    parser.add_argument('--list-events', action='store_true', help='列出事件')
    parser.add_argument('--stats', action='store_true', help='显示统计')
    parser.add_argument('--test', action='store_true', help='运行测试')
    
    args = parser.parse_args()
    
    gep = GEPAssets()
    
    if args.create_gene:
        # 示例：创建一个 Gene
        gene = gep.create_gene(
            name='API 超时修复',
            description='检测并修复 API 超时问题',
            triggers=[
                {
                    'type': 'error',
                    'keywords': ['超时', 'timeout', 'API'],
                }
            ],
            actions=[
                {
                    'type': 'remember',
                    'content': '增加超时时间到 30 秒',
                },
                {
                    'type': 'remember',
                    'content': '添加重试机制（最多 3 次）',
                }
            ],
            tags=['api', 'error', 'timeout']
        )
        
        print(f"✅ 创建 Gene: {gene['name']} ({gene['id']})")
    
    elif args.list_genes:
        genes = gep.list_genes()
        
        print(f"📋 Genes ({len(genes)} 个)\n")
        
        for gene in genes:
            print(f"  {gene['name']} ({gene['id']})")
            print(f"    描述: {gene['description']}")
            print(f"    使用次数: {gene['usage_count']}")
            print(f"    成功率: {gene['success_count']}/{gene['success_count'] + gene['failure_count']}")
            print()
    
    elif args.list_events:
        events = gep.get_events(limit=20)
        
        print(f"📝 最近事件 ({len(events)} 条)\n")
        
        for event in events:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp']))
            print(f"  [{timestamp}] {event['type']}")
            print(f"    {event['details']}")
            print()
    
    elif args.stats:
        stats = gep.get_stats()
        
        print("📊 GEP 资产统计\n")
        print(f"  Genes: {stats['genes']['total']} 个")
        print(f"    总使用次数: {stats['genes']['total_usage']}")
        print(f"    成功率: {stats['genes']['success_rate']:.1%}")
        print()
        print(f"  Capsules: {stats['capsules']['total']} 个")
        print(f"    总使用次数: {stats['capsules']['total_usage']}")
        print()
        print(f"  Events: {stats['events']['total']} 条")
        print(f"    最近 24 小时: {stats['events']['recent_24h']} 条")
    
    elif args.test:
        print("🧪 测试 GEP 资产管理\n")
        
        # 创建测试 Gene
        gene1 = gep.create_gene(
            name='飞书 API 限流处理',
            description='检测并处理飞书 API 限流',
            triggers=[
                {'type': 'error', 'keywords': ['飞书', '限流', '429']},
            ],
            actions=[
                {'type': 'remember', 'content': '分段请求，每批 50 条'},
                {'type': 'remember', 'content': '添加 1 秒延迟'},
            ],
            tags=['feishu', 'api', 'rate-limit']
        )
        
        print(f"✅ 创建 Gene: {gene1['name']}")
        
        # 测试信号匹配
        test_signals = [
            {
                'type': 'error',
                'content': '飞书 API 返回 429 限流错误',
                'confidence': 0.9,
            }
        ]
        
        result = gep.select_best_gene(test_signals)
        
        if result:
            gene, score = result
            print(f"✅ 匹配到 Gene: {gene['name']} (分数: {score:.2f})")
        else:
            print("❌ 未匹配到 Gene")
        
        # 更新使用统计
        gep.update_gene_usage(gene1['id'], success=True)
        print(f"✅ 更新使用统计")
        
        # 显示统计
        stats = gep.get_stats()
        print(f"\n📊 统计: {stats['genes']['total']} 个 Genes, {stats['events']['total']} 条事件")
    
    else:
        parser.print_help()
