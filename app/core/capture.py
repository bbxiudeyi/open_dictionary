"""屏幕捕获:物理像素截图 + 逻辑/物理坐标换算。

坑位说明(务必读):
- mss 工作在物理像素坐标系;Qt 窗口工作在逻辑像素。
- 高分屏缩放(125%/150%)下,框选的 logical QRect 必须乘以
  QScreen.devicePixelRatio() 并减去屏幕几何原点,才能得到该屏幕
  冻结帧(物理尺寸 QImage)内的像素区域。所有换算集中在本文件。
"""

from __future__ import annotations

import logging

import mss
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QScreen

logger = logging.getLogger(__name__)


class ScreenService:
    """截图与坐标换算的统一入口。"""

    @staticmethod
    def logical_to_physical(rect: QRect, screen: QScreen) -> tuple[int, int, int, int]:
        """全局逻辑坐标矩形 → 该屏幕冻结帧内的物理像素矩形。"""
        dpr = screen.devicePixelRatio()
        geo = screen.geometry()
        return (
            round((rect.x() - geo.x()) * dpr),
            round((rect.y() - geo.y()) * dpr),
            round(rect.width() * dpr),
            round(rect.height() * dpr),
        )

    @staticmethod
    def screen_physical_rect(screen: QScreen) -> dict:
        """QScreen → mss 的 monitor 字典(物理像素,虚拟桌面坐标)。"""
        dpr = screen.devicePixelRatio()
        geo = screen.geometry()
        return {
            "left": round(geo.x() * dpr),
            "top": round(geo.y() * dpr),
            "width": round(geo.width() * dpr),
            "height": round(geo.height() * dpr),
        }

    @staticmethod
    def grab_physical(x: int, y: int, w: int, h: int) -> QImage:
        """按物理像素抓取任意区域(虚拟桌面坐标系)。"""
        mss_factory = getattr(mss, "MSS", mss.mss)  # mss>=10 类名改为 MSS,兼容旧版
        with mss_factory() as sct:
            # 夹紧到虚拟桌面范围(原点可能为负:副屏在主屏左侧时),越界 mss 会抛错
            vx, vy, vw, vh = (
                sct.monitors[0]["left"],
                sct.monitors[0]["top"],
                sct.monitors[0]["width"],
                sct.monitors[0]["height"],
            )
            x, y = max(vx, x), max(vy, y)
            w = max(1, min(w, vx + vw - x))
            h = max(1, min(h, vy + vh - y))
            shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
            # mss>=10 移除了 .data/.bytes_per_line,用 .bgra + 手动计算行宽
            bpl = shot.width * 4
            image = QImage(shot.bgra, shot.width, shot.height, bpl, QImage.Format_ARGB32)
            return image.copy()  # 底层缓冲不保证长期有效,必须深拷贝

    def grab_screen(self, screen: QScreen) -> QImage:
        """抓取某个屏幕的冻结帧(物理尺寸)。"""
        mon = self.screen_physical_rect(screen)
        return self.grab_physical(mon["left"], mon["top"], mon["width"], mon["height"])
