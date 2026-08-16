"""框选遮罩:冻结屏 + 半透明覆盖 + 拖拽选区。

多显示器:每个 QScreen 一个全屏遮罩窗口,共享一个 CaptureSession;
只有发生鼠标按下的那个窗口成为"选择窗口",其余静默。
ESC 取消。选区以全局逻辑坐标 QRect 报出,同时回传裁剪好的 QImage
(从冻结帧裁剪,而非松手时重新截屏——所见即所得)。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from app.core.capture import ScreenService

logger = logging.getLogger(__name__)

_COLOR_DIM = QColor(0, 0, 0, 110)
_COLOR_ACCENT = QColor("#3b82f6")
_COLOR_TEXT = QColor("#ffffff")
_MIN_SELECTION = 4  # 小于该尺寸视为误触,等同取消


class CaptureOverlay(QWidget):
    """单个屏幕上的全屏遮罩。"""

    def __init__(self, screen, frozen: QImage, session: "CaptureSession") -> None:
        super().__init__(None)
        self._screen = screen
        self._session = session
        self._frozen = QPixmap.fromImage(frozen)
        self._origin: QPoint | None = None  # 鼠标按下点(本窗口局部坐标)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(screen.geometry())

    # ---- 绘制 ----
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        scaled = self._frozen.scaled(self.size())
        painter.drawPixmap(0, 0, scaled)
        painter.fillRect(self.rect(), _COLOR_DIM)
        sel = self._selection_rect()
        if sel is not None and sel.width() > 2 and sel.height() > 2:
            painter.drawPixmap(sel, scaled, sel)  # 选区恢复原亮度
            painter.setPen(QPen(_COLOR_ACCENT, 2))
            painter.drawRect(sel)
            painter.setPen(QPen(_COLOR_TEXT))
            painter.drawText(
                sel.x() + 4,
                max(14, sel.y() - 6),
                f"{sel.width()} x {sel.height()}  松开鼠标开始翻译",
            )
        painter.end()

    def _selection_rect(self) -> QRect | None:
        if self._origin is None or self._session.current_pos is None:
            return None
        if self._session.selector is not self:
            return None
        return QRect(self._origin, self._session.current_pos).normalized()

    # ---- 交互 ----
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._session.selector = self
            self._origin = event.position().toPoint()
            self._session.current_pos = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self._session.current_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        sel = self._selection_rect()
        self._origin = None
        if sel is None or sel.width() < _MIN_SELECTION or sel.height() < _MIN_SELECTION:
            self._session.cancel()
            return
        global_rect = QRect(self.mapToGlobal(sel.topLeft()), sel.size())
        self._session.finish(global_rect, self._screen, self._frozen)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._session.cancel()


class CaptureSession(QObject):
    """一次框选会话:管理所有屏幕的遮罩并汇拢结果。"""

    region_selected = Signal(object, object, object)  # QImage, QRect(全局逻辑), QScreen
    canceled = Signal()

    def __init__(self, screen_service: ScreenService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = screen_service
        self._overlays: list[CaptureOverlay] = []
        self.current_pos = None
        self.selector: CaptureOverlay | None = None

    def start(self) -> None:
        for screen in QGuiApplication.screens():
            frozen = self._service.grab_screen(screen)
            overlay = CaptureOverlay(screen, frozen, self)
            self._overlays.append(overlay)
        for overlay in self._overlays:
            overlay.show()
            overlay.raise_()
        if self._overlays:
            self._overlays[0].activateWindow()

    def finish(self, global_rect: QRect, screen, frozen: QPixmap) -> None:
        """从冻结帧裁剪选区(物理像素)并结束会话。"""
        dpr = screen.devicePixelRatio()
        geo = screen.geometry()
        src = QRect(
            round((global_rect.x() - geo.x()) * dpr),
            round((global_rect.y() - geo.y()) * dpr),
            round(global_rect.width() * dpr),
            round(global_rect.height() * dpr),
        )
        src = src.intersected(QRect(0, 0, frozen.width(), frozen.height()))
        image = frozen.toImage().copy(src)
        self._teardown()
        self.region_selected.emit(image, global_rect, screen)

    def cancel(self) -> None:
        self._teardown()
        self.canceled.emit()

    def _teardown(self) -> None:
        for overlay in self._overlays:
            overlay.close()
            overlay.deleteLater()
        self._overlays.clear()
        self.selector = None
        self.current_pos = None
