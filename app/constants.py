"""全局常量:默认值、语言表、模型仓库信息。"""

from __future__ import annotations

APP_NAME = "open-dictionary"
APP_DISPLAY_NAME = "Open Dictionary"
APP_VERSION = "0.1.0"

# ---- 默认设置 ----
DEFAULT_CAPTURE_HOTKEY = "ctrl+alt+t"  # 截图翻译
DEFAULT_QUERY_HOTKEY = "ctrl+alt+q"  # 输入翻译
DEFAULT_TARGET_LANG = "zho_Hans"
DEFAULT_SOURCE_LANG = "auto"  # auto = 字符集启发判断
DEFAULT_HF_ENDPOINT = "https://hf-mirror.com"  # 国内可达的 HF 镜像,可改回 https://huggingface.co

# ---- 支持的目标语言(NLLB-200 语言代码)----
# 顺序即设置界面下拉框顺序。
SUPPORTED_LANGUAGES: dict[str, str] = {
    "zho_Hans": "简体中文",
    "zho_Hant": "繁體中文",
    "eng_Latn": "英语",
    "jpn_Jpan": "日语",
    "kor_Hang": "韩语",
    "fra_Latn": "法语",
    "deu_Latn": "德语",
    "rus_Latn": "俄语",
    "spa_Latn": "西班牙语",
    "por_Latn": "葡萄牙语",
    "ita_Latn": "意大利语",
    "vie_Latn": "越南语",
    "tha_Thai": "泰语",
    "ara_Arab": "阿拉伯语",
    "hin_Deva": "印地语",
    "ind_Latn": "印尼语",
    "tur_Latn": "土耳其语",
}

# ---- NLLB 模型(HuggingFace 上的 CTranslate2 int8 预转换版)----
# 注意:文件名以仓库实际内容为准,若 404 请到仓库页面核对后调整本表,
# 或参照 docs/DEVELOPMENT.md 用 ct2-transformers-converter 本地转换。
# config.json 必不可少:CTranslate2 缺了它会把 token 配置当作 null,
# 报 "type must be string, but is null"。
NLLB_MODEL_DIRNAME = "nllb-200-distilled-600M-ct2-int8"
NLLB_MODEL_REPO = "JustFrederik/nllb-200-distilled-600M-ct2-int8"
NLLB_MODEL_FILES: list[tuple[str, int]] = [
    # (文件名, 最小字节数,用于完整性校验)
    ("model.bin", 550 * 1024 * 1024),  # 实际 622,595,991 字节(593.7 MiB)
    ("shared_vocabulary.txt", 2_500_000),
    ("config.json", 100),
]

# 分词器文件(来自官方仓库,AutoTokenizer use_fast=True 需要)
TOKENIZER_REPO = "facebook/nllb-200-distilled-600M"
TOKENIZER_FILES: list[tuple[str, int]] = [
    ("sentencepiece.bpe.model", 4 * 1024 * 1024),
    ("tokenizer_config.json", 1),
    ("special_tokens_map.json", 1),
    ("tokenizer.json", 1),
]
