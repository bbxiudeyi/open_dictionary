"""日志初始化:滚动文件 + 控制台,UTF-8。"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.paths import ensure_dirs, log_file

_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"


def init(level: int = logging.INFO) -> None:
    ensure_dirs()
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:  # 防止重复初始化(测试里多次调用)
        return

    file_handler = RotatingFileHandler(
        log_file(), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(console)

    # 第三方库降噪
    for noisy in ("PIL", "urllib3", "filelock"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
