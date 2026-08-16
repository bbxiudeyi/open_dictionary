"""系统托盘:常驻入口 + 菜单。

菜单只保留 生词本 / 设置 / 退出;截图与输入翻译的入口是全局热键
(以及单击托盘 = 截图翻译)。语言切换时重建菜单。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app import i18n


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
    open_vocab = Signal()
    open_settings = Signal()
    quit = Signal()
    # 单击托盘 = 快捷截图入口
    capture_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(make_tray_icon())
        self.tray.activated.connect(self._on_activated)
        self._hotkey_hint = ""
        self._rebuild()
        self.tray.show()

    def apply_language(self, settings) -> None:
        """语言或热键设置变化后调用:重建菜单与提示。"""
        self._hotkey_hint = settings.capture_hotkey
        self._rebuild()

    def _rebuild(self) -> None:
        self.tray.setToolTip(
            f"Open Dictionary — {i18n.tr('tray_tag')}({self._hotkey_hint})"
            if self._hotkey_hint
            else f"Open Dictionary — {i18n.tr('tray_tag')}"
        )
        menu = QMenu()
        act_vocab = QAction(i18n.tr("menu_vocab"), menu)
        act_vocab.triggered.connect(self.open_vocab.emit)
        act_settings = QAction(i18n.tr("menu_settings"), menu)
        act_settings.triggered.connect(self.open_settings.emit)
        act_quit = QAction(i18n.tr("menu_quit"), menu)
        act_quit.triggered.connect(self.quit.emit)
        menu.addAction(act_vocab)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)

    def show_message(self, title: str, message: str, msecs: int = 4000) -> None:
        """托盘气泡通知(main.py 里 flow.status 信号的出口)。"""
        self.tray.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, msecs
        )

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.capture_requested.emit()
