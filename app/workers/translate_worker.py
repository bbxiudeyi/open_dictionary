"""翻译任务:文本 → 译文。"""

from __future__ import annotations

from typing import Callable

from app.core.nllb import NllbTranslator
from app.workers import run_in_thread


def start_translate_task(
    translator: NllbTranslator,
    text: str,
    src_lang: str,
    tgt_lang: str,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    run_in_thread(
        translator.translate, on_done, on_error, text, src_lang, tgt_lang, timeout_ms=30_000
    )
