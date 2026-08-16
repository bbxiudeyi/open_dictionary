"""OCR 任务:截图 → 识别文本。"""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QImage

from app.core.ocr import OcrEngine
from app.workers import run_in_thread


def start_ocr_task(
    engine: OcrEngine,
    image: QImage,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    """在线程池中识别图片,返回合并后的文本。"""

    def work() -> str:
        lines = engine.recognize(image)
        return engine.lines_to_text(lines)

    run_in_thread(work, on_done, on_error, timeout_ms=60_000)
