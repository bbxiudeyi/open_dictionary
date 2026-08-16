"""设置数据模型:字段、默认值、校验。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from app import constants


@dataclass
class AppSettings:
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
        errors: list[str] = []
        if not self.capture_hotkey or "+" not in self.capture_hotkey:
            errors.append("截图快捷键不能为空,且需包含修饰键(如 ctrl+alt+t)")
        if not self.query_hotkey or "+" not in self.query_hotkey:
            errors.append("输入翻译快捷键不能为空,且需包含修饰键")
        if self.capture_hotkey == self.query_hotkey:
            errors.append("两个快捷键不能相同")
        if self.target_lang not in constants.SUPPORTED_LANGUAGES:
            errors.append(f"不支持的目标语言:{self.target_lang}")
        if self.source_lang != "auto" and self.source_lang not in constants.SUPPORTED_LANGUAGES:
            errors.append(f"不支持的源语言:{self.source_lang}")
        return errors
