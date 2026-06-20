#!/usr/bin/env python3
"""
Auto Memory Collector
自动记忆采集器 - 从对话中自动提取值得记录的内容
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import sys

# Add current directory to path for evolve import
sys.path.insert(0, str(Path(__file__).parent))
import evolve

logger = logging.getLogger("auto-memory-collector")


@dataclass
class Memory:
    """记忆数据结构"""
    type: str  # fact, preference, skill, error, pattern, insight
    content: str
    importance: float
    extracted_entity: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ContentFilter:
    """内容过滤器 - 过滤噪音消息"""

    MIN_LENGTH = 10  # 最少 10 个字符

    NOISE_PATTERNS = [
        r'^(好的|OK|知道了|明白|收到|谢谢|感谢|继续|下一步|开始吧)$',
        r'^(是的|对|没错|对的|嗯|啊|哦)$',
        r'^Tool results provided\.$',
    ]

    def should_skip(self, text: str) -> bool:
        """判断是否应跳过此内容"""
        text = text.strip()

        # 太短
        if len(text) < self.MIN_LENGTH:
            return True

        # 纯噪音
        for pattern in self.NOISE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        # 纯代码块（不记录代码本身）
        if text.startswith('```') and text.endswith('```'):
            return True

        return False


class PreferenceDetector:
    """偏好识别器"""

    PATTERNS = [
        (r'我(喜欢|偏好|更喜欢)(.+)', 0.85),
        (r'我(不喜欢|讨厌|不要)(.+)', 0.85),
        (r'我(习惯|通常|一般)(.+)', 0.75),
        (r'(更喜欢|prefer)\s*(.+?)\s*(而不是|over)\s*(.+)', 0.80),
    ]

    def detect(self, text: str) -> Optional[Memory]:
        """检测偏好声明"""
        for pattern, score in self.PATTERNS:
            if match := re.search(pattern, text, re.IGNORECASE):
                return Memory(
                    type='preference',
                    content=text.strip(),
                    importance=score,
                    extracted_entity=match.group(2).strip() if len(match.groups()) >= 2 else None
                )
        return None


class DecisionDetector:
    """决策识别器"""

    PATTERNS = [
        (r'(决定|选择|确定)(用|使用|采用)?\s*(.+)', 0.90),
        (r'(使用|采用|引入)\s*(.+?)\s*(来|做|重构|实现)', 0.85),
        (r'(改为|切换到|迁移到)\s*(.+)', 0.85),
        (r'(不用|放弃|废弃)\s*(.+?)[,，](因为|原因是)(.+)', 0.80),
    ]

    def detect(self, text: str) -> Optional[Memory]:
        """检测决策声明"""
        for pattern, score in self.PATTERNS:
            if match := re.search(pattern, text, re.IGNORECASE):
                return Memory(
                    type='preference',  # 决策也归类为偏好
                    content=text.strip(),
                    importance=score,
                    extracted_entity=match.group(3).strip() if len(match.groups()) >= 3 else None
                )
        return None


class ErrorDetector:
    """错误识别器 - 最有价值的记忆类型"""

    ERROR_KEYWORDS = ['错误', '报错', '失败', 'error', 'bug', '问题', '踩坑', 'exception', 'failed']
    SOLUTION_KEYWORDS = ['解决', '修复', '改为', 'fixed', 'solved', '方案', '通过']

    def detect(self, text: str) -> Optional[Memory]:
        """检测错误 + 解决方案"""
        text_lower = text.lower()

        has_error = any(kw in text_lower for kw in self.ERROR_KEYWORDS)
        has_solution = any(kw in text_lower for kw in self.SOLUTION_KEYWORDS)

        if has_error and has_solution:
            # 错误 + 解决方案 = 最有价值
            return Memory(
                type='error',
                content=text.strip(),
                importance=0.95,
                tags=['solution']
            )
        elif has_error and len(text) > 30:
            # 仅有问题描述（但足够详细）
            return Memory(
                type='error',
                content=text.strip(),
                importance=0.80,
                tags=['problem']
            )

        return None


class KnowledgeDetector:
    """知识识别器"""

    PATTERNS = [
        (r'(原来|发现|了解到|才知道)(.+)', 0.75),
        (r'(.+?)(可以|能够|支持)(.+)', 0.70),
    ]

    def detect(self, text: str) -> Optional[Memory]:
        """检测知识声明"""
        for pattern, score in self.PATTERNS:
            if match := re.search(pattern, text, re.IGNORECASE):
                # 知识片段需要足够长才有价值
                if len(text) >= 20:
                    return Memory(
                        type='insight',
                        content=text.strip(),
                        importance=score
                    )
        return None


class ImportanceScorer:
    """重要性评分器"""

    TECH_KEYWORDS = {
        'react', 'next.js', 'typescript', 'python', 'sqlite', 'postgresql',
        'api', 'mcp', 'github', 'git', 'docker', 'kubernetes', 'aws',
        'fastapi', 'flask', 'django', 'supabase', 'vercel', 'claude',
        'anthropic', 'openai', 'gpt', 'llm', 'embedding', 'vector',
        'database', 'cache', 'redis', 'mongodb', 'mysql', 'prisma'
    }

    def score(self, memory: Memory, context: Dict[str, Any]) -> float:
        """
        多维度评分

        Args:
            memory: 待评分的记忆
            context: 上下文信息（当前任务等）

        Returns:
            最终分数 (0-1)
        """
        base_score = memory.importance

        # 长度加成（20-100 字最佳）
        length = len(memory.content)
        length_bonus = 0
        if 20 <= length <= 100:
            length_bonus = 0.05
        elif length > 100:
            length_bonus = 0.10  # 详细内容更有价值

        # 实体密度（技术名词）
        tech_entities = self._extract_tech_entities(memory.content)
        entity_bonus = min(len(tech_entities) * 0.02, 0.10)

        # 上下文相关性（如果与当前任务相关）
        context_bonus = 0
        if context.get('current_task'):
            if self._is_relevant(memory.content, context['current_task']):
                context_bonus = 0.10

        final_score = min(base_score + length_bonus + entity_bonus + context_bonus, 1.0)
        return final_score

    def _extract_tech_entities(self, text: str) -> List[str]:
        """识别技术实体"""
        text_lower = text.lower()
        return [kw for kw in self.TECH_KEYWORDS if kw in text_lower]

    def _is_relevant(self, content: str, task: str) -> bool:
        """检查内容是否与任务相关（简单版本）"""
        # 提取任务关键词
        task_words = set(re.findall(r'\w+', task.lower()))
        content_words = set(re.findall(r'\w+', content.lower()))

        # 计算交集
        overlap = task_words & content_words
        return len(overlap) >= 2  # 至少 2 个共同词


class DeduplicateChecker:
    """去重检查器"""

    SIMILARITY_THRESHOLD = 0.80  # 80% 相似度视为重复

    def is_duplicate(self, new_memory: Memory) -> bool:
        """检查是否重复"""
        try:
            # 查询最近 100 条同类型记忆
            recent_memories = evolve.search_memories(
                query=f"type:{new_memory.type}",
                limit=100
            )

            for existing in recent_memories:
                # 精确匹配
                if existing['content'] == new_memory.content:
                    logger.debug(f"Exact duplicate found: {existing['id']}")
                    return True

                # 模糊匹配（编辑距离）
                similarity = self._calculate_similarity(
                    existing['content'],
                    new_memory.content
                )
                if similarity > self.SIMILARITY_THRESHOLD:
                    logger.debug(f"Similar memory found (score={similarity:.2f}): {existing['id']}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False  # 出错时不阻止记录

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算文本相似度（基于编辑距离）"""
        import difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio()


class AutoMemoryCollector:
    """自动记忆采集器 - 主类"""

    def __init__(self):
        """初始化采集器"""
        self.filter = ContentFilter()
        self.detectors = [
            PreferenceDetector(),
            DecisionDetector(),
            ErrorDetector(),
            KnowledgeDetector(),
        ]
        self.scorer = ImportanceScorer()
        self.deduplicator = DeduplicateChecker()

        self.stats = {
            "processed": 0,
            "skipped": 0,
            "collected": 0,
            "duplicated": 0
        }

        logger.info("AutoMemoryCollector initialized")

    def process_message(self, text: str, context: Dict[str, Any] = None) -> Optional[int]:
        """
        处理一条消息

        Args:
            text: 消息文本
            context: 上下文信息

        Returns:
            记忆 ID（如果记录成功），否则 None
        """
        if context is None:
            context = {}

        self.stats["processed"] += 1

        # 1. 内容过滤
        if self.filter.should_skip(text):
            self.stats["skipped"] += 1
            logger.debug(f"Skipped: {text[:50]}...")
            return None

        # 2. 规则引擎检测
        detected_memory = None
        for detector in self.detectors:
            memory = detector.detect(text)
            if memory:
                detected_memory = memory
                logger.info(f"Detected {memory.type}: {text[:50]}...")
                break  # 使用第一个匹配的检测器

        if not detected_memory:
            logger.debug(f"No pattern matched: {text[:50]}...")
            return None

        # 3. 重要性评分
        final_score = self.scorer.score(detected_memory, context)

        # 分数过低，丢弃
        if final_score < 0.60:
            logger.debug(f"Score too low ({final_score:.2f}): {text[:50]}...")
            return None

        detected_memory.importance = final_score

        # 4. 去重检查
        if self.deduplicator.is_duplicate(detected_memory):
            self.stats["duplicated"] += 1
            logger.info(f"Duplicate skipped: {text[:50]}...")
            return None

        # 5. 写入数据库
        try:
            memory_id = evolve.add_memory(
                content=detected_memory.content,
                mem_type=detected_memory.type,
                tags=",".join(detected_memory.tags) if detected_memory.tags else "",
                importance=detected_memory.importance,
                short_term=1,  # 默认进入短期记忆
                long_term=0
            )

            self.stats["collected"] += 1
            logger.info(f"✅ Memory collected (ID={memory_id}, score={final_score:.2f}): {text[:50]}...")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to save memory: {e}", exc_info=True)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["collected"] / self.stats["processed"]
                if self.stats["processed"] > 0 else 0
            )
        }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    collector = AutoMemoryCollector()

    # 测试用例
    test_messages = [
        # 应该被采集
        "我喜欢用 TypeScript 而不是 JavaScript",
        "决定用 Next.js 重构前端",
        "遇到数据库锁定错误，修改为单一事务解决了",
        "原来 SQLite 支持 FTS5 全文搜索",

        # 应该被跳过
        "好的",
        "继续",
        "Tool results provided.",

        # 应该被过滤（太短）
        "知道了"
    ]

    print("=== Testing Auto Memory Collector ===\n")

    for msg in test_messages:
        print(f"Input: {msg}")
        result = collector.process_message(msg)
        print(f"Result: {'✅ Collected' if result else '⏭️  Skipped'}")
        print()

    print("=== Stats ===")
    import json
    print(json.dumps(collector.get_stats(), indent=2))
