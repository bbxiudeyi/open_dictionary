"""设置对话框:快捷键、目标语言、自动入词库、模型下载。"""

from __future__ import annotations

import logging
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app import constants
from app.core.model_store import ModelStore
from app.core.nllb import NllbTranslator
from app.settings.models import AppSettings
from app.settings.store import SettingsStore
from app.ui.widgets.hotkey_edit import HotkeyEdit
from app.workers import run_in_thread

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    def __init__(
        self,
        store: SettingsStore,
        model_store: ModelStore,
        translator: NllbTranslator,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)
        self._store = store
        self._model_store = model_store
        self._translator = translator
        self._cancel_event = None

        s = store.settings
        layout = QVBoxLayout(self)

        # ---- 快捷键 ----
        hk_box = QGroupBox("快捷键")
        hk_layout = QVBoxLayout(hk_box)
        row1 = QVBoxLayout()
        row1.addWidget(QLabel("截图翻译"))
        self.capture_hotkey = HotkeyEdit(s.capture_hotkey)
        row1.addWidget(self.capture_hotkey)
        row2 = QVBoxLayout()
        row2.addWidget(QLabel("输入翻译"))
        self.query_hotkey = HotkeyEdit(s.query_hotkey)
        row2.addWidget(self.query_hotkey)
        hk_layout.addLayout(row1)
        hk_layout.addLayout(row2)
        layout.addWidget(hk_box)

        # ---- 翻译 ----
        tr_box = QGroupBox("翻译")
        tr_layout = QVBoxLayout(tr_box)
        tr_layout.addWidget(QLabel("目标语言"))
        self.target_lang = QComboBox()
        for code, name in constants.SUPPORTED_LANGUAGES.items():
            self.target_lang.addItem(name, code)
        self.target_lang.setCurrentIndex(
            max(0, list(constants.SUPPORTED_LANGUAGES).index(s.target_lang))
            if s.target_lang in constants.SUPPORTED_LANGUAGES
            else 0
        )
        tr_layout.addWidget(self.target_lang)
        self.auto_save = QCheckBox("翻译结果自动加入生词本")
        self.auto_save.setChecked(s.auto_save_vocab)
        tr_layout.addWidget(self.auto_save)
        layout.addWidget(tr_box)

        # ---- 模型 ----
        model_box = QGroupBox("翻译模型(NLLB-200-600M,本地离线)")
        model_layout = QVBoxLayout(model_box)
        self.model_status = QLabel()
        model_layout.addWidget(self.model_status)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        model_layout.addWidget(self.progress)
        self.download_btn = QPushButton("下载 / 校验模型")
        self.download_btn.clicked.connect(self._start_download)
        model_layout.addWidget(self.download_btn)
        layout.addWidget(model_box)

        # ---- 确定 / 取消 ----
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_model_status()

    # ---- 模型下载 ----
    def _refresh_model_status(self) -> None:
        if self._model_store.is_ready():
            self.model_status.setText("✓ 模型已就绪,可以离线翻译")
            self.download_btn.setEnabled(False)
        else:
            missing = self._model_store.missing_files()
            self.model_status.setText(f"✗ 模型未就绪(约 600MB),缺 {len(missing)} 个文件")
            self.download_btn.setEnabled(True)

    def _start_download(self) -> None:
        if not self.download_btn.isEnabled():
            return
        self.download_btn.setText("下载中…(点击取消)")
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self._cancel)
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)

        def on_progress(frac: float, detail: str) -> None:
            self.progress.setValue(int(frac * 100))
            self.model_status.setText(detail)

        def on_done(_=None) -> None:
            self._restore_download_btn()
            self._refresh_model_status()
            # 后台预热,下次热键即用
            run_in_thread(self._translator.ensure_loaded, None, None)

        def on_error(msg: str) -> None:
            self._restore_download_btn()
            self.model_status.setText(f"下载失败:{msg}")

        cancel_event = threading.Event()

        def work() -> None:
            self._model_store.download(on_progress, cancel_event)

        self._cancel_event = cancel_event
        run_in_thread(work, on_done, on_error)

    def _cancel(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    def _restore_download_btn(self) -> None:
        try:
            self.download_btn.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.download_btn.clicked.connect(self._start_download)
        self.download_btn.setText("下载 / 校验模型")
        self.progress.setVisible(False)

    # ---- 保存 ----
    def _save(self) -> None:
        new = AppSettings(
            capture_hotkey=self.capture_hotkey.combo(),
            query_hotkey=self.query_hotkey.combo(),
            target_lang=self.target_lang.currentData(),
            source_lang=self._store.settings.source_lang,
            auto_save_vocab=self.auto_save.isChecked(),
            hf_endpoint=self._store.settings.hf_endpoint,
            model_dir=self._store.settings.model_dir,
        )
        errors = self._store.save(new)
        if errors:
            QMessageBox.warning(self, "设置有误", "\n".join(errors))
            return
        self.accept()

    def show_and_focus(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
