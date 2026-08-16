"""NLLB 翻译测试。

- detect_language / 同语种翻转:无模型依赖,默认跑。
- translate:需要本地模型,标记 slow,用 `pytest -m slow` 运行。
"""

from __future__ import annotations

import pytest

from app.core.nllb import NllbTranslator, detect_language
from app.paths import models_dir
from app import constants


def test_detect_language():
    assert detect_language("Hello world") == "eng_Latn"
    assert detect_language("你好,世界") == "zho_Hans"
    assert detect_language("こんにちは") == "jpn_Jpan"
    assert detect_language("안녕하세요") == "kor_Hang"
    assert detect_language("Привет") == "rus_Latn"


@pytest.mark.slow
def test_translate_en_to_zh():
    model_dir = models_dir() / constants.NLLB_MODEL_DIRNAME
    translator = NllbTranslator(model_dir)
    translator.ensure_loaded()  # 显式加载,失败信息更清晰
    result = translator.translate("Knowledge is power.", "eng_Latn", "zho_Hans")
    assert result.strip()
    assert result != "Knowledge is power."
    assert "知识" in result or "力量" in result  # 宽松断言,允许译文措辞差异
