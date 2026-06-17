#!/usr/bin/env python3
"""
Configuration loader for DNA Memory MCP Server
"""

import os
import json
from pathlib import Path

# Default paths
DEFAULT_MEMORY_DIR = Path.home() / ".openclaw/workspace/dna-memory/memory"
DEFAULT_CONFIG_PATH = Path.home() / ".openclaw/workspace/dna-memory/assets/config.json"


def get_memory_dir() -> Path:
    """Get memory directory from environment or default"""
    env_path = os.getenv("DNA_MEMORY_DIR")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_MEMORY_DIR


def get_config_path() -> Path:
    """Get config file path from environment or default"""
    env_path = os.getenv("DNA_MEMORY_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_CONFIG_PATH


def load_config() -> dict:
    """Load configuration from file"""
    config_path = get_config_path()
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
    return {}


def get_log_level() -> str:
    """Get log level from environment"""
    return os.getenv("DNA_MEMORY_LOG_LEVEL", "INFO")
