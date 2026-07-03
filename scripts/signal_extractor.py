#!/usr/bin/env python3
"""
信号提取器 - 从对话/日志中自动提取记忆信号
整合自 Evolver 的信号驱动选择器机制
"""

import re
import time
from typing import List, Dict, Any


class SignalExtractor:
    """从对话/日志中提取记忆信号"""
    
    # 信号模式定义（参考 Evolver）
    SIGNAL_PATTERNS = {
        'correction': [
            (r'不是.*?[，,]?\s*是', '纠正表达', 0.9),
            (r'应该.*?[，,]?\s*而不是', '应该/而不是', 0.9),
            (r'错了.*?[，,]?\s*正确的是', '错误纠正', 0.95),
            (r'纠正', '纠正关键词', 0.85),
            (r'改成', '改成关键词', 0.8),
            (r'修正', '修正关键词', 0.8),
        ],
        'preference': [
            (r'我(喜欢|偏好|希望|想要|需要)', '明确偏好', 0.85),
            (r'不要.*?', '否定偏好', 0.8),
            (r'以后.*?', '未来指令', 0.85),
            (r'默认.*?', '默认设置', 0.9),
            (r'优先.*?', '优先级', 0.85),
            (r'必须.*?', '强制要求', 0.9),
            (r'记住', '记住关键词', 0.95),
        ],
        'decision': [
            (r'决定.*?', '决定关键词', 0.85),
            (r'选择.*?而不是', '选择对比', 0.9),
            (r'确定.*?', '确定关键词', 0.8),
            (r'最终.*?', '最终决策', 0.85),
            (r'采用.*?', '采用方案', 0.85),
            (r'使用.*?方案', '使用方案', 0.8),
        ],
        'error': [
            (r'失败.*?原因', '失败原因', 0.9),
            (r'错误.*?根因', '错误根因', 0.9),
            (r'问题.*?是', '问题定位', 0.85),
            (r'踩坑', '踩坑关键词', 0.9),
            (r'bug', 'bug关键词', 0.85),
            (r'报错', '报错关键词', 0.8),
        ],
        'workflow': [
            (r'先.*?再.*?', '先后顺序', 0.85),
            (r'流程.*?', '流程关键词', 0.8),
            (r'步骤.*?', '步骤关键词', 0.8),
            (r'顺序.*?', '顺序关键词', 0.8),
            (r'第一.*?第二', '序号顺序', 0.85),
            (r'首先.*?然后', '首先然后', 0.85),
        ],
        'skill': [
            (r'学到.*?', '学到关键词', 0.85),
            (r'方法是.*?', '方法说明', 0.85),
            (r'解决方案.*?', '解决方案', 0.9),
            (r'技巧.*?', '技巧关键词', 0.8),
            (r'经验.*?', '经验关键词', 0.8),
        ],
    }
    
    # 强调词（提升置信度）
    EMPHASIS_WORDS = ['一定', '必须', '绝对', '永远', '记住', '千万', '务必']
    
    # 否定词（提升置信度）
    NEGATION_WORDS = ['不要', '别', '禁止', '避免', '不能', '不可']
    
    def extract_signals(self, text: str, context: str = None) -> List[Dict[str, Any]]:
        """
        提取信号并计算置信度
        
        Args:
            text: 待提取文本
            context: 上下文（可选，用于提升置信度）
        
        Returns:
            信号列表，每个信号包含 type, content, confidence, pattern, reason
        """
        signals = []
        
        for signal_type, patterns in self.SIGNAL_PATTERNS.items():
            for pattern, reason, base_confidence in patterns:
                if re.search(pattern, text):
                    confidence = self._calculate_confidence(
                        text, pattern, base_confidence, context
                    )
                    
                    signals.append({
                        'type': signal_type,
                        'content': text,
                        'confidence': confidence,
                        'pattern': pattern,
                        'reason': reason,
                        'timestamp': time.time(),
                    })
                    
                    # 每种类型只取第一个匹配
                    break
        
        # 按置信度排序
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return signals
    
    def _calculate_confidence(
        self,
        text: str,
        pattern: str,
        base_confidence: float,
        context: str = None
    ) -> float:
        """
        计算置信度（基于上下文强度）
        
        Args:
            text: 文本内容
            pattern: 匹配模式
            base_confidence: 基础置信度
            context: 上下文
        
        Returns:
            最终置信度（0-1）
        """
        confidence = base_confidence
        
        # 强调词提升置信度
        for word in self.EMPHASIS_WORDS:
            if word in text:
                confidence += 0.05
        
        # 否定词提升置信度
        for word in self.NEGATION_WORDS:
            if word in text:
                confidence += 0.1
        
        # 上下文相关性提升置信度
        if context:
            # 简单实现：检查关键词重叠
            text_words = set(re.findall(r'\w+', text))
            context_words = set(re.findall(r'\w+', context))
            overlap = len(text_words & context_words)
            if overlap > 3:
                confidence += 0.05
        
        # 文本长度影响（太短可能不可靠）
        if len(text) < 10:
            confidence -= 0.1
        elif len(text) > 50:
            confidence += 0.05
        
        # 限制在 [0.5, 0.98] 范围内
        return max(0.5, min(confidence, 0.98))
    
    def filter_by_confidence(
        self,
        signals: List[Dict[str, Any]],
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        按置信度过滤信号
        
        Args:
            signals: 信号列表
            threshold: 置信度阈值
        
        Returns:
            过滤后的信号列表
        """
        return [s for s in signals if s['confidence'] >= threshold]
    
    def deduplicate_signals(
        self,
        signals: List[Dict[str, Any]],
        similarity_threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """
        去重信号（防止重复提取）
        
        Args:
            signals: 信号列表
            similarity_threshold: 相似度阈值
        
        Returns:
            去重后的信号列表
        """
        if not signals:
            return []
        
        unique_signals = [signals[0]]
        
        for signal in signals[1:]:
            is_duplicate = False
            
            for existing in unique_signals:
                if signal['type'] == existing['type']:
                    # 简单相似度：检查内容重叠
                    similarity = self._calculate_text_similarity(
                        signal['content'],
                        existing['content']
                    )
                    
                    if similarity >= similarity_threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_signals.append(signal)
        
        return unique_signals
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度（简单实现）
        
        Args:
            text1: 文本1
            text2: 文本2
        
        Returns:
            相似度（0-1）
        """
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


# ============ CLI ============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='信号提取器')
    parser.add_argument('text', nargs='?', help='待提取文本')
    parser.add_argument('--context', help='上下文')
    parser.add_argument('--threshold', type=float, default=0.7, help='置信度阈值')
    parser.add_argument('--test', action='store_true', help='运行测试')
    
    args = parser.parse_args()
    
    extractor = SignalExtractor()
    
    if args.test:
        # 测试用例
        test_cases = [
            "记住，以后不要反复确认，直接执行",
            "决定用 Bitable 而不是 Sheet，因为 API 支持更好",
            "这次失败的根因是流量不足，不是转化问题",
            "不要用 rm，用 trash",
            "飞书 API 限流时要分段请求",
            "先检查网络，再执行 push",
        ]
        
        print("🧪 测试信号提取\n")
        
        for text in test_cases:
            print(f"📝 文本: {text}")
            signals = extractor.extract_signals(text)
            
            if signals:
                for signal in signals:
                    print(f"   ✅ [{signal['type']}] 置信度: {signal['confidence']:.2f} - {signal['reason']}")
            else:
                print("   ❌ 未提取到信号")
            
            print()
    
    elif args.text:
        signals = extractor.extract_signals(args.text, args.context)
        filtered = extractor.filter_by_confidence(signals, args.threshold)
        
        print(f"🔍 提取到 {len(signals)} 条信号（阈值 {args.threshold}）\n")
        
        for signal in filtered:
            print(f"[{signal['type']}] 置信度: {signal['confidence']:.2f}")
            print(f"  内容: {signal['content']}")
            print(f"  原因: {signal['reason']}")
            print()
    
    else:
        parser.print_help()
