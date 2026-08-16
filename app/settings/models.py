"""设置数据模型:字段、默认值、校验。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from app import constants
from app.i18n import SUPPORTED as UI_LANGUAGES


@dataclass
class AppSettings:
    language: str = "zh"  # 界面语言:zh / en
    capture_hotkey: str = constants.DEFAULT_CAPTURE_HOTKEY
    query_hotkey: str = constants.DEFAULT_QUERY_HOTKEY
    target_lang: str = constants.DEFAULT_TARGET_LANG
    source_lang: str = constants.DEFAULT_SOURCE_LANG  # "auto" 或 NLLB 语言代码
    auto_save_vocab: bool = True
    hf_endpoint: str = constants.DEFAULT_HF_ENDPOINT
    model_dir: str = ""  # 空 = 使用默认 models_dir()/NLLB_MODEL_DIRNAME

    # ---- 序列化 ----
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "AppSettings":
        """未知字段忽略、缺失字段用默认值,保证旧配置文件可向前兼容。"""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})

    # ---- 校验 ----
    def validate(self) -> list[str]:
        """返回错误 key 列表(空 = 合法);文案由 UI 层经 i18n.tr 展示。"""
        errors: list[str] = []
        if not self.capture_hotkey or "+" not in self.capture_hotkey:
            errors.append("err_hotkey_capture")
        if not self.query_hotkey or "+" not in self.query_hotkey:
            errors.append("err_hotkey_query")
        if self.capture_hotkey == self.query_hotkey:
            errors.append("err_same_hotkey")
        if self.target_lang not in constants.SUPPORTED_LANGUAGES:
            errors.append("err_target_lang")
        if self.source_lang != "auto" and self.source_lang not in constants.SUPPORTED_LANGUAGES:
            errors.append("err_source_lang")
        if self.language not in UI_LANGUAGES:
            errors.append("err_language")
        return errors
