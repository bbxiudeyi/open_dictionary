"""OCR 引擎封装(RapidOCR / PP-OCR ONNX)。

惰性初始化:import 和模型加载都不发生在启动期,
第一次调用 recognize() 才加载(在线程池里,不卡 UI)。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import numpy as np
from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)


@dataclass
class OcrLine:
    box: list  # 四个角点坐标
    text: str
    score: float


class OcrEngine:
    def __init__(self) -> None:
        self._engine = None

    def ensure_loaded(self) -> None:
        """加载 OCR 模型(幂等)。"""
        if self._engine is not None:
            return
        try:
            from rapidocr_onnxruntime import RapidOCR  # 常规安装
        except ImportError:
            from rapidocr import RapidOCR  # rapidocr v2 统一包
        self._engine = RapidOCR()
        logger.info("OCR 引擎已加载")

    def recognize(self, image: QImage) -> list[OcrLine]:
        """对截图做 OCR,返回按阅读顺序(先上后下、先左后右)排列的行。"""
        self.ensure_loaded()
        arr = qimage_to_ndarray(image)
        result, _elapse = self._engine(arr)
        if not result:
            return []
        lines = [
            OcrLine(box=item[0], text=str(item[1]).strip(), score=float(item[2]))
            for item in result
            if str(item[1]).strip()
        ]
        lines.sort(key=lambda l: (min(p[1] for p in l.box), min(p[0] for p in l.box)))
        return lines

    @staticmethod
    def lines_to_text(lines: list[OcrLine]) -> str:
        """OCR 行合并为文本:物理上同一行的左右片段用空格拼接,行与行换行。"""
        if not lines:
            return ""
        rows: list[list[OcrLine]] = []
        for line in lines:
            y = min(p[1] for p in line.box)
            h = max(p[1] for p in line.box) - y
            for row in rows:
                row_y = min(min(p[1] for p in l.box) for l in row)
                if abs(y - row_y) <= max(4.0, h * 0.5):  # 高度重叠过半算同一行
                    row.append(line)
                    break
            else:
                rows.append([line])
        out: list[str] = []
        for row in rows:
            row.sort(key=lambda l: min(p[0] for p in l.box))
            out.append(" ".join(l.text for l in row))
        return "\n".join(out)


def qimage_to_ndarray(image: QImage) -> np.ndarray:
    """QImage → HxWx3(BGR) ndarray,供 OCR 使用。"""
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = image.width(), image.height()
    buf = image.constBits()
    arr = np.frombuffer(buf, dtype=np.uint8, count=h * w * 4).reshape(h, w, 4)
    rgb = arr[:, :, :3]
    return np.ascontiguousarray(rgb[:, :, ::-1])  # RGB → BGR
