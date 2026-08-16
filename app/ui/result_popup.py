"""翻译结果浮窗:显示在框选区域右侧,ESC 关闭。

定位策略:优先选区右侧 12px;右侧放不下 → 左侧;都不行 → 下方。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app import i18n

logger = logging.getLogger(__name__)

_MARGIN = 12
_MIN_WIDTH = 340
_MAX_WIDTH = 460
_MIN_HEIGHT = 130
_MAX_HEIGHT = 360


class ResultPopup(QFrame):
    def __init__(self) -> None:
        super().__init__(None)
        self._anchor_rect: QRect | None = None
        self._avail: QRect | None = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        self.source_label.setStyleSheet("color:#64748b; font-size:12px;")
        self.source_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setObjectName("result")
        self.result_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.copy_btn = QPushButton(i18n.tr("popup_copy"))
        self.copy_btn.setFixedHeight(24)
        self.copy_btn.clicked.connect(self._copy)
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)

        self.hint = QLabel(i18n.tr("popup_hint"))
        self.hint.setStyleSheet("color:#94a3b8; font-size:11px;")
        btns = QHBoxLayout()
        btns.addWidget(self.hint)
        btns.addStretch(1)
        btns.addWidget(self.copy_btn)
        btns.addWidget(self.close_btn)

        body = QVBoxLayout()
        body.setContentsMargins(14, 12, 14, 10)
        body.addWidget(self.source_label)
        body.addSpacing(6)
        body.addWidget(self.result_label)
        body.addLayout(btns)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner.setLayout(body)
        scroll.setWidget(inner)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setStyleSheet(
            "ResultPopup{background:#ffffff;border:2px solid #3b82f6;"
            "border-radius:8px;}"
            "QLabel#result{font-size:16px; font-weight:600; color:#0f172a;}"
        )

    def set_result(self, source: str, translated: str) -> None:
        self.source_label.setText(source)
        self.result_label.setText(translated)

    def update_result(self, source: str, translated: str) -> None:
        """原地更新内容(占位 → 识别中 → 译文),不重建窗口。"""
        self.set_result(source, translated)
        self.adjustSize()
        self.resize(
            max(_MIN_WIDTH, min(self.width(), _MAX_WIDTH)),
            max(_MIN_HEIGHT, min(self.height(), _MAX_HEIGHT)),
        )
        if self._anchor_rect is not None and self._avail is not None:
            self._place_near(self._anchor_rect, self._avail)
        self.raise_()

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.result_label.text())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    # ---- 定位 ----
    @classmethod
    def show_near(cls, anchor: QRect, screen, source: str, translated: str) -> "ResultPopup":
        popup = cls()
        popup.set_result(source, translated)
        popup.adjustSize()
        popup.resize(
            max(_MIN_WIDTH, min(popup.width(), _MAX_WIDTH)),
            max(_MIN_HEIGHT, min(popup.height(), _MAX_HEIGHT)),
        )
        popup._place_near(anchor, screen.availableGeometry())
        popup.show()
        popup.raise_()
        popup.activateWindow()  # 拿焦点,ESC 才能关
        popup.setFocus()
        logger.info("结果浮窗已显示:%s", popup.geometry())
        return popup

    def _place_near(self, anchor: QRect, avail: QRect) -> None:
        self._anchor_rect, self._avail = anchor, avail
        w, h = self.width(), self.height()
        # 1) 右侧
        x = anchor.right() + _MARGIN
        if x + w <= avail.right():
            pos = (x, anchor.top())
        else:
            # 2) 左侧
            lx = anchor.left() - _MARGIN - w
            if lx >= avail.left():
                pos = (lx, anchor.top())
            else:
                # 3) 下方
                pos = (anchor.left(), anchor.bottom() + _MARGIN)
        x, y = pos
        x = max(avail.left(), min(x, avail.right() - w))
        y = max(avail.top(), min(y, avail.bottom() - h))
        self.move(x, y)
