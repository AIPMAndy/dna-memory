#!/usr/bin/env python3
"""
Agent 适配器 - 让 DNA Memory 支持多种 AI Agent
支持: Claude CLI, Hermes
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

class AgentAdapter:
    """统一的 Agent 调用接口"""

    SUPPORTED_AGENTS = ['claude', 'hermes']

    def __init__(self, agent_name: str = 'claude'):
        """
        初始化 Agent 适配器

        Args:
            agent_name: Agent 名称 (claude, hermes)
        """
        if agent_name not in self.SUPPORTED_AGENTS:
            raise ValueError(f"不支持的 Agent: {agent_name}. 支持: {self.SUPPORTED_AGENTS}")

        self.agent_name = agent_name
        self.agent_path = self._find_agent()

        if not self.agent_path:
            raise FileNotFoundError(f"未找到 {agent_name} 命令")

    def _find_agent(self) -> Optional[str]:
        """查找 Agent 可执行文件路径"""
        # 尝试 which 命令
        try:
            result = subprocess.run(
                ['which', self.agent_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        # 尝试常见路径
        common_paths = [
            Path.home() / '.local' / 'bin' / self.agent_name,
            Path('/usr/local/bin') / self.agent_name,
            Path('/opt/homebrew/bin') / self.agent_name,
        ]

        for path in common_paths:
            if path.exists() and path.is_file():
                return str(path)

        return None

    def call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        调用 Agent

        Args:
            prompt: 提示词
            **kwargs: 其他参数
                - model: 模型名称
                - temperature: 温度
                - max_tokens: 最大 token 数
                - cwd: 工作目录

        Returns:
            {
                'success': bool,
                'response': str,
                'error': str (if failed)
            }
        """
        if self.agent_name == 'claude':
            return self._call_claude(prompt, **kwargs)
        elif self.agent_name == 'hermes':
            return self._call_hermes(prompt, **kwargs)
        else:
            return {
                'success': False,
                'error': f'未实现的 Agent: {self.agent_name}'
            }

    def _call_claude(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """调用 Claude CLI"""
        cmd = [str(self.agent_path), '-p', prompt]

        # 添加参数
        if 'model' in kwargs and kwargs['model']:
            cmd.extend(['--model', kwargs['model']])

        if 'cwd' in kwargs and kwargs['cwd']:
            cmd.extend(['--cwd', str(kwargs['cwd'])])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=kwargs.get('timeout', 60)
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'response': result.stdout.strip(),
                    'agent': 'claude'
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr.strip() or result.stdout.strip(),
                    'agent': 'claude'
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Claude CLI 超时',
                'agent': 'claude'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'调用 Claude CLI 失败: {str(e)}',
                'agent': 'claude'
            }

    def _call_hermes(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """调用 Hermes"""
        cmd = [str(self.agent_path), '-z', prompt]

        # 添加参数
        if 'model' in kwargs and kwargs['model']:
            cmd.extend(['-m', kwargs['model']])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=kwargs.get('timeout', 60)
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'response': result.stdout.strip(),
                    'agent': 'hermes'
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr.strip() or result.stdout.strip(),
                    'agent': 'hermes'
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Hermes 超时',
                'agent': 'hermes'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'调用 Hermes 失败: {str(e)}',
                'agent': 'hermes'
            }

    def check_availability(self) -> Dict[str, Any]:
        """检查 Agent 可用性"""
        # 简单检查文件是否存在且可执行
        if not self.agent_path:
            return {
                'agent': self.agent_name,
                'path': None,
                'available': False,
                'error': f'{self.agent_name} 命令不存在'
            }

        path_obj = Path(self.agent_path)
        if not path_obj.exists():
            return {
                'agent': self.agent_name,
                'path': self.agent_path,
                'available': False,
                'error': '文件不存在'
            }

        if not os.access(self.agent_path, os.X_OK):
            return {
                'agent': self.agent_name,
                'path': self.agent_path,
                'available': False,
                'error': '文件不可执行'
            }

        # 测试简单调用（快速测试）
        test_result = self.call("respond with 'ok'", timeout=30)

        return {
            'agent': self.agent_name,
            'path': self.agent_path,
            'available': test_result['success'],
            'test_response': test_result.get('response', '')[:50] if test_result['success'] else None,
            'error': test_result.get('error') if not test_result['success'] else None
        }


def detect_available_agents() -> list:
    """检测所有可用的 Agent"""
    available = []

    for agent_name in AgentAdapter.SUPPORTED_AGENTS:
        try:
            adapter = AgentAdapter(agent_name)
            status = adapter.check_availability()
            if status['available']:
                available.append(status)
        except Exception as e:
            pass

    return available


def get_default_agent() -> Optional[str]:
    """获取默认 Agent（优先级: Claude > Hermes）"""
    for agent_name in ['claude', 'hermes']:
        try:
            adapter = AgentAdapter(agent_name)
            if adapter.check_availability()['available']:
                return agent_name
        except Exception:
            continue

    return None


# ============ CLI ============
def main():
    import argparse

    parser = argparse.ArgumentParser(description='Agent 适配器 - 统一调用多种 AI Agent')
    parser.add_argument('action', choices=['list', 'test', 'call'], help='操作')
    parser.add_argument('--agent', choices=AgentAdapter.SUPPORTED_AGENTS, help='指定 Agent')
    parser.add_argument('--prompt', help='提示词（用于 call）')
    parser.add_argument('--model', help='模型名称')

    args = parser.parse_args()

    if args.action == 'list':
        print("🤖 检测可用的 AI Agent")
        print("=" * 50)

        available = detect_available_agents()

        if not available:
            print("❌ 未找到可用的 Agent")
            return

        for status in available:
            print(f"\n✅ {status['agent']}")
            print(f"   路径: {status['path']}")
            print(f"   测试: {status['test_response']}")

        print(f"\n默认 Agent: {get_default_agent()}")

    elif args.action == 'test':
        agent_name = args.agent or get_default_agent()

        if not agent_name:
            print("❌ 未找到可用的 Agent")
            return

        print(f"🧪 测试 {agent_name}")
        print("=" * 50)

        try:
            adapter = AgentAdapter(agent_name)
            status = adapter.check_availability()

            if status['available']:
                print(f"✅ {agent_name} 可用")
                print(f"   路径: {status['path']}")
                print(f"   响应: {status['test_response']}")
            else:
                print(f"❌ {agent_name} 不可用")
                print(f"   错误: {status['error']}")
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")

    elif args.action == 'call':
        if not args.prompt:
            print("❌ 请指定 --prompt")
            return

        agent_name = args.agent or get_default_agent()

        if not agent_name:
            print("❌ 未找到可用的 Agent")
            return

        print(f"🤖 使用 {agent_name} 执行...")
        print("=" * 50)

        try:
            adapter = AgentAdapter(agent_name)
            result = adapter.call(args.prompt, model=args.model)

            if result['success']:
                print(f"\n✅ 响应:\n{result['response']}")
            else:
                print(f"\n❌ 失败: {result['error']}")
        except Exception as e:
            print(f"❌ 调用失败: {str(e)}")


if __name__ == '__main__':
    main()
