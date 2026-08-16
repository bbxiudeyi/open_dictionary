"""设置持久化:JSON 原子写 + 变更信号。

只在主线程使用(设置读写频率极低,无并发需求)。
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.settings.models import AppSettings

logger = logging.getLogger(__name__)


class SettingsStore(QObject):
    changed = Signal(object)  # AppSettings

    def __init__(self, path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._settings = self._load()

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def _load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            settings = AppSettings.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("配置文件损坏,备份后使用默认配置:%s", exc)
            backup = self._path.with_suffix(".json.bak")
            try:
                shutil.copy2(self._path, backup)
            except OSError:
                pass
            return AppSettings()
        errors = settings.validate()
        if errors:
            logger.warning("配置校验失败(%s),使用默认配置", errors)
            return AppSettings()
        return settings

    def save(self, new: AppSettings) -> list[str]:
        """校验并保存;返回错误列表(空 = 成功)。成功后发出 changed 信号。"""
        errors = new.validate()
        if errors:
            return errors
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(new.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)  # 原子替换,断电不会写坏
        self._settings = new
        self.changed.emit(new)
        logger.info("设置已更新:%s", new.to_dict())
        return []
