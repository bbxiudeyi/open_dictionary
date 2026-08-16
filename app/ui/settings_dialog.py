"""设置对话框:语言、快捷键、目标语言、自动入词库、模型下载。"""

from __future__ import annotations

import logging
import threading

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

from app import constants, i18n
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
        self.setWindowTitle(i18n.tr("settings_title"))
        self.setMinimumWidth(420)
        self._store = store
        self._model_store = model_store
        self._translator = translator
        self._cancel_event = None

        s = store.settings
        layout = QVBoxLayout(self)

        # ---- 通用(语言) ----
        gen_box = QGroupBox(i18n.tr("grp_general"))
        gen_layout = QVBoxLayout(gen_box)
        gen_layout.addWidget(QLabel(i18n.tr("lbl_ui_lang")))
        self.ui_language = QComboBox()
        for code, name in i18n.SUPPORTED.items():
            self.ui_language.addItem(name, code)
        self.ui_language.setCurrentIndex(
            max(0, list(i18n.SUPPORTED).index(s.language)) if s.language in i18n.SUPPORTED else 0
        )
        gen_layout.addWidget(self.ui_language)
        layout.addWidget(gen_box)

        # ---- 快捷键 ----
        hk_box = QGroupBox(i18n.tr("grp_hotkeys"))
        hk_layout = QVBoxLayout(hk_box)
        row1 = QVBoxLayout()
        row1.addWidget(QLabel(i18n.tr("lbl_capture_hotkey")))
        self.capture_hotkey = HotkeyEdit(s.capture_hotkey)
        row1.addWidget(self.capture_hotkey)
        row2 = QVBoxLayout()
        row2.addWidget(QLabel(i18n.tr("lbl_query_hotkey")))
        self.query_hotkey = HotkeyEdit(s.query_hotkey)
        row2.addWidget(self.query_hotkey)
        hk_layout.addLayout(row1)
        hk_layout.addLayout(row2)
        layout.addWidget(hk_box)

        # ---- 翻译 ----
        tr_box = QGroupBox(i18n.tr("grp_translate"))
        tr_layout = QVBoxLayout(tr_box)
        tr_layout.addWidget(QLabel(i18n.tr("lbl_target_lang")))
        self.target_lang = QComboBox()
        for code, name in constants.SUPPORTED_LANGUAGES.items():
            self.target_lang.addItem(name, code)
        self.target_lang.setCurrentIndex(
            max(0, list(constants.SUPPORTED_LANGUAGES).index(s.target_lang))
            if s.target_lang in constants.SUPPORTED_LANGUAGES
            else 0
        )
        tr_layout.addWidget(self.target_lang)
        self.auto_save = QCheckBox(i18n.tr("chk_auto_save"))
        self.auto_save.setChecked(s.auto_save_vocab)
        tr_layout.addWidget(self.auto_save)
        layout.addWidget(tr_box)

        # ---- 模型 ----
        model_box = QGroupBox(i18n.tr("grp_model"))
        model_layout = QVBoxLayout(model_box)
        self.model_status = QLabel()
        model_layout.addWidget(self.model_status)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        model_layout.addWidget(self.progress)
        self.download_btn = QPushButton(i18n.tr("btn_download"))
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
            self.model_status.setText(i18n.tr("model_ready"))
            self.download_btn.setEnabled(False)
        else:
            missing = self._model_store.missing_files()
            self.model_status.setText(i18n.tr("model_missing_n").format(len(missing)))
            self.download_btn.setEnabled(True)

    def _start_download(self) -> None:
        if not self.download_btn.isEnabled():
            return
        self.download_btn.setText(i18n.tr("btn_downloading"))
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
            run_in_thread(self._translator.ensure_loaded, None, None)  # 后台预热

        def on_error(msg: str) -> None:
            self._restore_download_btn()
            self.model_status.setText(i18n.tr("download_failed").format(msg))

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
        self.download_btn.setText(i18n.tr("btn_download"))
        self.progress.setVisible(False)

    # ---- 保存 ----
    def _save(self) -> None:
        new = AppSettings(
            language=self.ui_language.currentData(),
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
            QMessageBox.warning(
                self, i18n.tr("settings_invalid"), "\n".join(i18n.tr(e) for e in errors)
            )
            return
        self.accept()

    def show_and_focus(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
