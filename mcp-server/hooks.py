#!/opt/homebrew/opt/python@3.11/bin/python3.11
"""
MCP Message Hooks
监听 Claude Code 对话消息，触发自动记忆采集
"""

import logging
import json
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

logger = logging.getLogger("dna-memory-hooks")


class MessageHook:
    """MCP 消息钩子"""

    def __init__(self, auto_collector=None):
        """
        初始化消息钩子

        Args:
            auto_collector: AutoMemoryCollector 实例（可选，延迟加载）
        """
        self.auto_collector = auto_collector
        self.enabled = True
        self.message_count = 0
        logger.info("MessageHook initialized")

    def on_message_updated(self, notification: Dict[str, Any]) -> None:
        """
        处理 notifications/messages/updated 事件

        MCP 协议规范：
        {
            "method": "notifications/messages/updated",
            "params": {
                "messages": [
                    {
                        "role": "user" | "assistant",
                        "content": {...}
                    }
                ]
            }
        }

        Args:
            notification: MCP 通知对象
        """
        if not self.enabled:
            logger.debug("Hook disabled, skipping message")
            return

        try:
            params = notification.get("params", {})
            messages = params.get("messages", [])

            if not messages:
                logger.debug("No messages in notification")
                return

            # 处理每条消息
            for message in messages:
                self._process_message(message)
                self.message_count += 1

        except Exception as e:
            logger.error(f"Error processing message notification: {e}", exc_info=True)

    def _process_message(self, message: Dict[str, Any]) -> None:
        """
        处理单条消息

        Args:
            message: 消息对象 {"role": "user"|"assistant", "content": {...}}
        """
        role = message.get("role")
        content = message.get("content")

        if not role or not content:
            logger.debug("Message missing role or content")
            return

        # 提取文本内容
        text = self._extract_text_content(content)
        if not text:
            logger.debug(f"No text content in {role} message")
            return

        logger.info(f"Processing {role} message: {text[:50]}...")

        # 延迟加载 auto_collector（避免循环导入）
        if self.auto_collector is None:
            try:
                from auto_memory_collector import AutoMemoryCollector
                self.auto_collector = AutoMemoryCollector()
                logger.info("AutoMemoryCollector loaded")
            except ImportError as e:
                logger.error(f"Failed to load AutoMemoryCollector: {e}")
                return

        # 触发自动采集
        try:
            # 只处理用户消息（用户的偏好、决策更有价值）
            # assistant 消息通常是代码/解释，价值较低
            if role == "user":
                self.auto_collector.process_message(text, context={
                    "role": role,
                    "message_id": self.message_count
                })
            else:
                # assistant 消息仅记录错误/教训
                if self._contains_error_keywords(text):
                    self.auto_collector.process_message(text, context={
                        "role": role,
                        "message_id": self.message_count
                    })

        except Exception as e:
            logger.error(f"Error in auto_collector.process_message: {e}", exc_info=True)

    def _extract_text_content(self, content: Any) -> Optional[str]:
        """
        从 content 中提取文本

        MCP content 可能的格式：
        - 字符串: "text content"
        - 对象: {"type": "text", "text": "content"}
        - 数组: [{"type": "text", "text": "content"}, ...]

        Args:
            content: MCP content 对象

        Returns:
            提取的文本，如果没有则返回 None
        """
        # 直接是字符串
        if isinstance(content, str):
            return content.strip()

        # 是对象
        if isinstance(content, dict):
            # {"type": "text", "text": "..."}
            if content.get("type") == "text":
                return content.get("text", "").strip()
            # {"text": "..."}
            if "text" in content:
                return content["text"].strip()

        # 是数组（多个 content block）
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif isinstance(item, str):
                    texts.append(item)

            if texts:
                return " ".join(texts).strip()

        return None

    def _contains_error_keywords(self, text: str) -> bool:
        """检查文本是否包含错误关键词"""
        ERROR_KEYWORDS = [
            '错误', '报错', '失败', 'error', 'bug', '问题', '踩坑',
            'exception', 'traceback', 'failed', '修复', '解决'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in ERROR_KEYWORDS)

    def enable(self) -> None:
        """启用消息钩子"""
        self.enabled = True
        logger.info("MessageHook enabled")

    def disable(self) -> None:
        """禁用消息钩子"""
        self.enabled = False
        logger.info("MessageHook disabled")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled": self.enabled,
            "message_count": self.message_count
        }


# 全局钩子实例（单例模式）
_hook_instance: Optional[MessageHook] = None


def get_message_hook() -> MessageHook:
    """获取全局消息钩子实例（单例）"""
    global _hook_instance
    if _hook_instance is None:
        _hook_instance = MessageHook()
    return _hook_instance


def register_hooks(server):
    """
    注册钩子到 MCP 服务器

    注意：MCP SDK 当前版本（截至 2026-06）尚未正式支持
    notifications/messages/updated 钩子。

    这是预留接口，等待 MCP 协议支持后启用。

    临时方案：通过 tool call 触发（见 server.py 中的 dna_remember）

    Args:
        server: MCP Server 实例
    """
    hook = get_message_hook()

    # TODO: 等待 MCP SDK 支持后启用
    # @server.on_notification("messages/updated")
    # async def on_message(notification):
    #     hook.on_message_updated(notification)

    logger.info("Message hooks registered (waiting for MCP protocol support)")
    return hook


if __name__ == "__main__":
    # 测试代码
    import doctest

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试消息提取
    hook = MessageHook()

    test_cases = [
        # 字符串格式
        {"role": "user", "content": "我喜欢用 TypeScript"},

        # 对象格式
        {"role": "user", "content": {"type": "text", "text": "决定用 Next.js"}},

        # 数组格式
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "遇到数据库锁定错误"},
                {"type": "text", "text": "修改为单一事务解决"}
            ]
        }
    ]

    for i, test_msg in enumerate(test_cases):
        print(f"\n--- Test {i+1} ---")
        text = hook._extract_text_content(test_msg["content"])
        print(f"Extracted: {text}")

    print("\n--- Stats ---")
    print(json.dumps(hook.get_stats(), indent=2))
