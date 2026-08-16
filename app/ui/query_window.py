"""输入翻译窗口(输入模式):输入文本 → 回车翻译 → 结果展示。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class QueryWindow(QWidget):
    def __init__(self, flow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Open Dictionary — 输入翻译")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint  # 查词场景常浮在上面
        )
        self.resize(420, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)

        self.input = QLineEdit()
        self.input.setPlaceholderText("输入要翻译的文本,回车翻译…")
        self.input.returnPressed.connect(self._translate)
        layout.addWidget(self.input)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("译文将显示在这里(同时自动加入生词本)")
        layout.addWidget(self.result, 1)

        self.status = QLabel(" ")
        self.status.setStyleSheet("color:#64748b;")
        layout.addWidget(self.status)

        self._flow = flow
        flow.result_ready.connect(self._on_result)
        flow.status.connect(self.status.setText)

    def _translate(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.status.setText("翻译中…")
        self._flow.translate_text(text)

    def _on_result(self, source: str, translated: str) -> None:
        self.result.setPlainText(translated)
        self.status.setText(" ")

    def show_and_focus(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()
        self.input.selectAll()
