"""系统托盘:常驻入口 + 菜单。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def make_tray_icon() -> QIcon:
    """程序化画一个图标(蓝底白"译"),避免携带资源文件。"""
    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2563eb"))
    painter.setPen(QColor("#1e40af"))
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    painter.setPen(QColor("#ffffff"))
    font = QFont()
    font.setPixelSize(38)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pix.rect(), 0x0084, "译")  # AlignCenter
    painter.end()
    return QIcon(pix)


class TrayController(QObject):
    capture_requested = Signal()
    open_query = Signal()
    open_vocab = Signal()
    open_settings = Signal()
    quit = Signal()

    def __init__(self, hotkey_hint: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(make_tray_icon())
        self.tray.setToolTip(f"Open Dictionary — 划词翻译({hotkey_hint})")
        menu = QMenu()
        act_capture = QAction(f"截图翻译({hotkey_hint})", menu)
        act_capture.triggered.connect(self.capture_requested.emit)
        act_query = QAction("输入翻译…", menu)
        act_query.triggered.connect(self.open_query.emit)
        act_vocab = QAction("生词本", menu)
        act_vocab.triggered.connect(self.open_vocab.emit)
        act_settings = QAction("设置", menu)
        act_settings.triggered.connect(self.open_settings.emit)
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self.quit.emit)
        for act in (act_capture, act_query, act_vocab, act_settings):
            menu.addAction(act)
        menu.addSeparator()
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        # 单击托盘 = 快捷入口
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def show_message(self, title: str, message: str, msecs: int = 4000) -> None:
        """托盘气泡通知(main.py 里 flow.status 信号的出口)。"""
        self.tray.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, msecs
        )

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.capture_requested.emit()
