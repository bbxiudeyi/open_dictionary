"""数据目录与文件路径解析。

所有运行期数据都放在系统应用数据目录;设置环境变量
OPEN_DICTIONARY_HOME 可重定向(测试 / 便携模式用)。
路径函数每次调用都重新解析,便于测试中切换环境变量。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_OVERRIDE = "OPEN_DICTIONARY_HOME"


def data_dir() -> Path:
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        return Path(override)
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        root = str(Path.home() / "Library" / "Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / "open-dictionary"


def config_path() -> Path:
    return data_dir() / "config.json"


def vocab_db_path() -> Path:
    return data_dir() / "vocab.db"


def logs_dir() -> Path:
    return data_dir() / "logs"


def models_dir() -> Path:
    return data_dir() / "models"


def log_file() -> Path:
    return logs_dir() / "app.log"


def ensure_dirs() -> None:
    for d in (data_dir(), logs_dir(), models_dir()):
        d.mkdir(parents=True, exist_ok=True)
