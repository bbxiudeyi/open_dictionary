"""快捷键录制控件:点击进入录制状态,按下组合键捕获,ESC 取消。

输出 keyboard 库风格字符串,如 "ctrl+alt+t"。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QPushButton

_MODIFIER_MAP = {
    Qt.KeyboardModifier.ControlModifier: "ctrl",
    Qt.KeyboardModifier.AltModifier: "alt",
    Qt.KeyboardModifier.ShiftModifier: "shift",
    Qt.KeyboardModifier.MetaModifier: "win",
}

# Qt.Key → keyboard 库按键名(仅需要的部分,遇到未映射键拒绝录制)
_KEY_MAP = {
    Qt.Key.Key_A: "a", Qt.Key.Key_B: "b", Qt.Key.Key_C: "c", Qt.Key.Key_D: "d",
    Qt.Key.Key_E: "e", Qt.Key.Key_F: "f", Qt.Key.Key_G: "g", Qt.Key.Key_H: "h",
    Qt.Key.Key_I: "i", Qt.Key.Key_J: "j", Qt.Key.Key_K: "k", Qt.Key.Key_L: "l",
    Qt.Key.Key_M: "m", Qt.Key.Key_N: "n", Qt.Key.Key_O: "o", Qt.Key.Key_P: "p",
    Qt.Key.Key_Q: "q", Qt.Key.Key_R: "r", Qt.Key.Key_S: "s", Qt.Key.Key_T: "t",
    Qt.Key.Key_U: "u", Qt.Key.Key_V: "v", Qt.Key.Key_W: "w", Qt.Key.Key_X: "x",
    Qt.Key.Key_Y: "y", Qt.Key.Key_Z: "z",
    Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2", Qt.Key.Key_3: "3",
    Qt.Key.Key_4: "4", Qt.Key.Key_5: "5", Qt.Key.Key_6: "6", Qt.Key.Key_7: "7",
    Qt.Key.Key_8: "8", Qt.Key.Key_9: "9",
    Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3", Qt.Key.Key_F4: "f4",
    Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6", Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8",
    Qt.Key.Key_F9: "f9", Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
    Qt.Key.Key_Space: "space", Qt.Key.Key_Print: "print screen",
}


class HotkeyEdit(QPushButton):
    changed = Signal(str)

    def __init__(self, combo: str = "", parent=None) -> None:
        super().__init__(parent)
        self._combo = combo
        self._recording = False
        self.setMinimumWidth(180)
        self._refresh()

    def combo(self) -> str:
        return self._combo

    def _refresh(self) -> None:
        if self._recording:
            self.setText("请按下组合键(ESC 取消)…")
        else:
            self.setText(self._combo or "(未设置)")

    def mousePressEvent(self, event) -> None:
        self._recording = True
        self._refresh()
        self.setFocus(Qt.FocusReason.MouseFocusReason)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._recording:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key in (Qt.Key.Key_Escape,):
            self._recording = False
            self._refresh()
            return
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return  # 修饰键本身不结束录制
        mods = [name for mod, name in _MODIFIER_MAP.items() if event.modifiers() & mod]
        main = _KEY_MAP.get(key)
        if main is None or not mods:
            self.setText("需包含修饰键(ctrl/alt/shift/win)+ 普通键")
            return
        self._combo = "+".join([*mods, main])
        self._recording = False
        self._refresh()
        self.changed.emit(self._combo)
        self.clearFocus()
