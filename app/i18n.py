"""界面语言(轻量 i18n)。

只有中英两种语言、几十条文案,不值得上 QTranslator/.ts/.qm 全家桶,
直接用字典 + tr()。语言由设置里的 language 字段驱动,main.py 启动时
和设置变更时调用 set_language()。已打开的窗口不动态重译,重新打开即生效。
"""

from __future__ import annotations

SUPPORTED: dict[str, str] = {"zh": "中文", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "tray_tag": "划词翻译",
        "menu_vocab": "生词本",
        "menu_settings": "设置",
        "menu_quit": "退出",
        "settings_title": "设置",
        "grp_general": "通用",
        "lbl_ui_lang": "界面语言(重新打开窗口后生效)",
        "grp_hotkeys": "快捷键",
        "lbl_capture_hotkey": "截图翻译",
        "lbl_query_hotkey": "输入翻译",
        "grp_translate": "翻译",
        "lbl_target_lang": "目标语言",
        "chk_auto_save": "翻译结果自动加入生词本",
        "grp_model": "翻译模型(NLLB-200-600M,本地离线)",
        "model_ready": "✓ 模型已就绪,可以离线翻译",
        "model_missing_n": "✗ 模型未就绪(约 600MB),缺 {} 个文件",
        "btn_download": "下载 / 校验模型",
        "btn_downloading": "下载中…(点击取消)",
        "download_failed": "下载失败:{}",
        "settings_invalid": "设置有误",
        "hotkey_recording": "请按下组合键(ESC 取消)…",
        "hotkey_unset": "(未设置)",
        "hotkey_need_mod": "需包含修饰键(ctrl/alt/shift/win)+ 普通键",
        "query_title": "Open Dictionary — 输入翻译",
        "query_placeholder": "输入要翻译的文本,回车翻译…",
        "query_result_hint": "译文将显示在这里(同时自动加入生词本)",
        "translating": "翻译中…",
        "recognizing": "识别中…",
        "ocr_empty": "未识别到文字",
        "ocr_failed": "OCR 失败:{}",
        "translate_failed": "翻译失败:{}",
        "popup_failed": "失败:{}",
        "popup_copy": "复制",
        "popup_hint": "ESC 关闭 · 已存入生词本",
        "overlay_hint": "松开鼠标开始翻译",
        "model_missing_status": "翻译模型未就绪,请先在设置中下载(约 600MB)",
        "task_timeout": "任务超时({}s),可重试",
        "vocab_title": "Open Dictionary — 生词本",
        "col_time": "时间",
        "col_source": "原文",
        "col_result": "译文",
        "col_origin": "来源",
        "vocab_search": "搜索原文 / 译文…",
        "vocab_refresh": "刷新",
        "vocab_delete": "删除该词条",
        # 设置校验错误 key(由对话框翻译展示)
        "err_hotkey_capture": "截图快捷键不能为空,且需包含修饰键(如 ctrl+alt+t)",
        "err_hotkey_query": "输入翻译快捷键不能为空,且需包含修饰键",
        "err_same_hotkey": "两个快捷键不能相同",
        "err_target_lang": "不支持的目标语言:{}",
        "err_source_lang": "不支持的源语言:{}",
        "err_language": "不支持的界面语言:{}",
    },
    "en": {
        "tray_tag": "Snap Translate",
        "menu_vocab": "Vocabulary",
        "menu_settings": "Settings",
        "menu_quit": "Quit",
        "settings_title": "Settings",
        "grp_general": "General",
        "lbl_ui_lang": "Language (takes effect on reopened windows)",
        "grp_hotkeys": "Hotkeys",
        "lbl_capture_hotkey": "Screenshot translate",
        "lbl_query_hotkey": "Input translate",
        "grp_translate": "Translation",
        "lbl_target_lang": "Target language",
        "chk_auto_save": "Auto-save translations to vocabulary",
        "grp_model": "Translation model (NLLB-200-600M, offline)",
        "model_ready": "✓ Model ready — offline translation available",
        "model_missing_n": "✗ Model missing (~600MB), {} file(s) missing",
        "btn_download": "Download / verify model",
        "btn_downloading": "Downloading… (click to cancel)",
        "download_failed": "Download failed: {}",
        "settings_invalid": "Invalid settings",
        "hotkey_recording": "Press keys (ESC to cancel)…",
        "hotkey_unset": "(not set)",
        "hotkey_need_mod": "Needs a modifier (ctrl/alt/shift/win) + a normal key",
        "query_title": "Open Dictionary — Translate",
        "query_placeholder": "Type text and press Enter…",
        "query_result_hint": "Translations appear here (auto-saved to vocabulary)",
        "translating": "Translating…",
        "recognizing": "Recognizing…",
        "ocr_empty": "No text detected",
        "ocr_failed": "OCR failed: {}",
        "translate_failed": "Translation failed: {}",
        "popup_failed": "Failed: {}",
        "popup_copy": "Copy",
        "popup_hint": "ESC to close · saved to vocabulary",
        "overlay_hint": "Release mouse to translate",
        "model_missing_status": "Model not ready — download it in Settings (~600MB)",
        "task_timeout": "Timed out ({}s), please retry",
        "vocab_title": "Open Dictionary — Vocabulary",
        "col_time": "Time",
        "col_source": "Original",
        "col_result": "Translation",
        "col_origin": "Source",
        "vocab_search": "Search original / translation…",
        "vocab_refresh": "Refresh",
        "vocab_delete": "Delete entry",
        "err_hotkey_capture": "Screenshot hotkey is invalid (needs a modifier, e.g. ctrl+alt+t)",
        "err_hotkey_query": "Input-translate hotkey is invalid (needs a modifier)",
        "err_same_hotkey": "The two hotkeys must differ",
        "err_target_lang": "Unsupported target language: {}",
        "err_source_lang": "Unsupported source language: {}",
        "err_language": "Unsupported UI language: {}",
    },
}

_current = "zh"


def set_language(lang: str) -> None:
    global _current
    _current = lang if lang in SUPPORTED else "zh"


def language() -> str:
    return _current


def tr(key: str) -> str:
    return STRINGS[_current].get(key) or STRINGS["zh"].get(key, key)
