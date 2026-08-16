"""Open Dictionary 入口。

启动顺序:日志 → 数据目录 → 单实例锁 → QApplication → 组装服务 → 托盘 → 事件循环。
"""

from __future__ import annotations

import os
import signal
import sys

# transformers 未装 PyTorch 属于刻意设计(只用它的分词器,推理走 CTranslate2),
# 静音"None of PyTorch, TensorFlow >= 2.0, or Flax have been found"提示。
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app import logging_setup
from app.constants import APP_DISPLAY_NAME, APP_VERSION
from app.controllers.translate_flow import TranslateFlow
from app.core.capture import ScreenService
from app.core.hotkey import HotkeyManager
from app.core.model_store import ModelStore
from app.core.nllb import NllbTranslator
from app.core.ocr import OcrEngine
from app.core.vocab import VocabStore
from app.paths import config_path, data_dir, ensure_dirs, models_dir, vocab_db_path
from app.settings.store import SettingsStore
from app.ui.query_window import QueryWindow
from app.ui.settings_dialog import SettingsDialog
from app.ui.tray import TrayController
from app.ui.vocab_window import VocabWindow
from app.workers import run_in_thread


def main() -> int:
    logging_setup.init()
    ensure_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)  # 关掉窗口不影响托盘常驻

    # 单实例:防止两个进程抢注热键
    lock = QLockFile(str(data_dir() / ".lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, APP_DISPLAY_NAME, "已有一个实例在运行。")
        return 0

    # ---- 服务层 ----
    settings_store = SettingsStore(config_path())
    settings = settings_store.settings
    vocab = VocabStore(vocab_db_path())
    model_store = ModelStore(models_dir(), endpoint=settings.hf_endpoint)
    ocr_engine = OcrEngine()
    translator = NllbTranslator(model_store.model_dir)

    # ---- 控制层 ----
    flow = TranslateFlow(
        settings_store=settings_store,
        screen=ScreenService(),
        ocr=ocr_engine,
        translator=translator,
        vocab=vocab,
        model_store=model_store,
    )

    # ---- 惰性窗口(单例) ----
    query_window: QueryWindow | None = None
    vocab_window: VocabWindow | None = None
    settings_dialog: SettingsDialog | None = None

    def open_query() -> None:
        nonlocal query_window
        if query_window is None:
            query_window = QueryWindow(flow)
        query_window.show_and_focus()

    def open_vocab() -> None:
        nonlocal vocab_window
        if vocab_window is None or not vocab_window.isVisible():
            vocab_window = VocabWindow(vocab)
        vocab_window.show_and_focus()

    def open_settings() -> None:
        nonlocal settings_dialog
        if settings_dialog is None or not settings_dialog.isVisible():
            settings_dialog = SettingsDialog(settings_store, model_store, translator)
        settings_dialog.show_and_focus()

    # ---- 全局热键 ----
    hotkeys = HotkeyManager()
    hotkeys.apply(settings)

    def on_hotkey(action: str) -> None:
        if action == "capture":
            flow.start_capture()
        elif action == "query":
            open_query()

    # ---- 托盘 ----
    tray = TrayController(hotkey_hint=settings.capture_hotkey)
    tray.capture_requested.connect(flow.start_capture)
    tray.open_query.connect(open_query)
    tray.open_vocab.connect(open_vocab)
    tray.open_settings.connect(open_settings)
    tray.quit.connect(app.quit)

    hotkeys.triggered.connect(on_hotkey)
    settings_store.changed.connect(hotkeys.apply)
    flow.status.connect(lambda msg: tray.show_message(APP_DISPLAY_NAME, msg))
    flow.model_missing.connect(open_settings)

    # Ctrl+C 退出支持:Qt 事件循环阻塞在 C++,主线程收不到 Python 信号,
    # 用定时器定期回到 Python 层让信号处理器得以执行(经典配方)。
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    wake_timer = QTimer(interval=200)
    wake_timer.timeout.connect(lambda: None)
    wake_timer.start()

    # 启动预热:OCR 与翻译引擎后台加载,首次使用不再等模型加载(各 1~2s)
    QTimer.singleShot(200, lambda: run_in_thread(ocr_engine.ensure_loaded, None, None))
    if model_store.is_ready():
        QTimer.singleShot(1500, lambda: run_in_thread(translator.ensure_loaded, None, None))

    app.aboutToQuit.connect(hotkeys.shutdown)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
