"""
    存放项目中的各种路径常量
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROMPT_DIR = PROJECT_ROOT / "Prompt"
CONFIG_DIR = PROJECT_ROOT / "Config"
STORAGE_DIR = PROJECT_ROOT / "storage"
LOGS_DIR = PROJECT_ROOT / "Log"