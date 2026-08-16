"""翻译主流程状态机(控制层)。

截图流程:热键 → 冻结屏 + 框选遮罩 → 裁剪 → OCR(线程池)→ 翻译(线程池)
         → 结果浮窗(选区右侧)→ 自动入词库 → ESC 清空。
输入流程:文本 → 翻译 → result_ready 信号(由 QueryWindow 展示)→ 入词库。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QRect, Signal
from PySide6.QtGui import QImage

from app.core.capture import ScreenService
from app.core.model_store import ModelStore
from app.core.nllb import NllbTranslator
from app.core.ocr import OcrEngine
from app.core.vocab import VocabStore
from app.settings.store import SettingsStore
from app.ui.capture_overlay import CaptureSession
from app.ui.result_popup import ResultPopup
from app.workers.ocr_worker import start_ocr_task
from app.workers.translate_worker import start_translate_task

logger = logging.getLogger(__name__)

MIN_REGION_SIZE = 8  # 小于该像素的框选视为误触


class TranslateFlow(QObject):
    status = Signal(str)  # 状态提示(托盘气泡)
    model_missing = Signal()
    result_ready = Signal(str, str)  # (原文, 译文) 输入模式用
    ocr_text = Signal(str)  # 调试/展示用

    def __init__(
        self,
        settings_store: SettingsStore,
        screen: ScreenService,
        ocr: OcrEngine,
        translator: NllbTranslator,
        vocab: VocabStore,
        model_store: ModelStore,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_store = settings_store
        self._screen = screen
        self._ocr = ocr
        self._translator = translator
        self._vocab = vocab
        self._model_store = model_store
        self._session: CaptureSession | None = None
        self._popup: ResultPopup | None = None

    @property
    def _settings(self):
        return self._settings_store.settings

    # ---- 截图翻译流程 ----
    def start_capture(self) -> None:
        if self._session is not None:
            return  # 已在框选中
        if not self._model_store.is_ready():
            self.status.emit("翻译模型未就绪,请先在设置中下载(约 600MB)")
            self.model_missing.emit()
            return
        self._close_popup()
        self._session = CaptureSession(self._screen)
        self._session.region_selected.connect(self._on_region)
        self._session.canceled.connect(self._on_canceled)
        self._session.start()

    def _on_canceled(self) -> None:
        self._session = None

    def _on_region(self, image: QImage, logical_rect: QRect, screen) -> None:
        self._session = None
        if image.width() < MIN_REGION_SIZE or image.height() < MIN_REGION_SIZE:
            return
        logger.info("框选区域 %dx%d(逻辑 %s)", image.width(), image.height(), logical_rect)
        self._anchor = (logical_rect, screen)
        # 浮窗立即占位:松开鼠标就出现"识别中…",完成后原地更新为译文。
        # 托盘气泡不当进度条用(Windows 气泡 5 秒固定时长且不即时替换,会残留旧状态)。
        self._ensure_popup("识别中…", "")

        def on_error(msg: str) -> None:
            self.status.emit(f"OCR 失败:{msg}")
            if self._popup is not None:
                self._popup.update_result(f"OCR 失败:{msg}", "")

        start_ocr_task(self._ocr, image, self._on_ocr_done, on_error)

    def _on_ocr_done(self, text: str) -> None:
        self.ocr_text.emit(text)
        if not text:
            if self._popup is not None:
                self._popup.update_result("未识别到文字", "")
            return
        self._translate_and_show(text, origin="ocr")

    def _translate_and_show(self, text: str, origin: str) -> None:
        tgt = self._settings.target_lang
        src = self._settings.source_lang

        def on_error(msg: str) -> None:
            self.status.emit(f"翻译失败:{msg}")
            if origin == "ocr" and self._popup is not None:
                self._popup.update_result(f"失败:{msg}", "")

        def on_done(result: str) -> None:
            if origin == "ocr" and self._popup is not None:
                self._popup.update_result(text, result)
            self.result_ready.emit(text, result)
            if self._settings.auto_save_vocab:
                from app.core.nllb import detect_language

                src_lang = src if src != "auto" else detect_language(text)
                self._vocab.add(text, result, src_lang, tgt, origin)

        start_translate_task(self._translator, text, src, tgt, on_done, on_error)

    def _ensure_popup(self, source: str, translated: str) -> None:
        self._close_popup()
        anchor = getattr(self, "_anchor", None)
        if anchor is None:
            logger.warning("缺少选区锚点,浮窗未显示")
            return
        rect, screen = anchor
        self._popup = ResultPopup.show_near(rect, screen, source, translated)

    def _close_popup(self) -> None:
        if self._popup is not None:
            self._popup.close()
            self._popup = None

    # ---- 输入翻译流程(输入模式) ----
    def translate_text(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if not self._model_store.is_ready():
            self.status.emit("翻译模型未就绪,请先在设置中下载(约 600MB)")
            self.model_missing.emit()
            return

        def on_error(msg: str) -> None:
            self.status.emit(f"翻译失败:{msg}")

        self._translate_and_show(text, origin="input")
