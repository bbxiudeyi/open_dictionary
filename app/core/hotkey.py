"""全局热键管理。

keyboard 库在自有的监听线程里回调,绝不能在回调里直接碰 UI;
这里只 emit Qt 信号,跨线程的信号会自动排队投递到主线程。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class HotkeyManager(QObject):
    triggered = Signal(str)  # 动作名:"capture" / "query"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._handles: dict[str, object] = {}

    def apply(self, settings) -> None:
        """按当前设置(重新)注册热键。"""
        self.unregister_all()
        self._register("capture", settings.capture_hotkey)
        self._register("query", settings.query_hotkey)

    def _register(self, action: str, combo: str) -> None:
        import keyboard  # 延迟导入,加快启动

        try:
            handle = keyboard.add_hotkey(
                combo,
                lambda a=action: self._on_fired(a),
                suppress=False,
                timeout=1,
            )
            self._handles[action] = handle
            logger.info("热键已注册:%s -> %s", action, combo)
        except Exception as exc:  # 无效组合 / 被占用
            logger.error("热键注册失败 %s(%s):%s", action, combo, exc)

    def _on_fired(self, action: str) -> None:
        # keyboard 回调在其监听线程执行;emit 到主线程槽是排队连接。
        try:
            self.triggered.emit(action)
        except RuntimeError as exc:  # 应用退出中,Qt 对象可能已销毁
            logger.debug("热键触发时应用正在退出:%s", exc)

    def unregister_all(self) -> None:
        import keyboard

        for action, handle in self._handles.items():
            try:
                keyboard.remove_hotkey(handle)
            except (KeyError, ValueError):
                pass  # 未注册成功或不存在的句柄
        self._handles.clear()

    def shutdown(self) -> None:
        self.unregister_all()
