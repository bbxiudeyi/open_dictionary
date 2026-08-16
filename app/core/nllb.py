"""NLLB-200-distilled-600M 翻译引擎(CTranslate2 int8,纯 CPU)。

- 模型目录由 ModelStore 负责下载/校验,这里只管推理。
- Translator 创建一次后复用;所有调用都发生在线程池的 worker 里。
- NLLB 单次输入上限约 512 token,超长文本自动分块翻译再拼接。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_SOURCE_TOKENS = 450  # 预留余量(NLLB 位置编码上限 512)


class NllbTranslator:
    def __init__(self, model_dir: Path) -> None:
        self._model_dir = Path(model_dir)
        self._translator = None
        self._tokenizer = None

    # ---- 生命周期 ----
    def ensure_loaded(self) -> None:
        """加载模型与分词器(幂等,约 1~2s)。"""
        if self._translator is not None:
            return
        import ctranslate2
        from transformers import AutoTokenizer

        self._translator = ctranslate2.Translator(
            str(self._model_dir), device="cpu", compute_type="int8"
        )
        tok_dir = self._model_dir / "tokenizer"
        self._tokenizer = AutoTokenizer.from_pretrained(str(tok_dir), use_fast=True)
        logger.info("NLLB 翻译引擎已加载:%s", self._model_dir)

    def reset(self) -> None:
        """模型重新下载后调用,丢弃旧实例。"""
        self._translator = None
        self._tokenizer = None

    # ---- 翻译 ----
    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """翻译一段文本。src_lang 为 "auto" 时自动检测。"""
        text = text.strip()
        if not text:
            return ""
        self.ensure_loaded()
        if src_lang == "auto":
            src_lang = detect_language(text)
        if src_lang == tgt_lang:  # 源目标同语种 → 翻到英语(除英语翻中文外)
            tgt_lang = "zho_Hans" if tgt_lang == "eng_Latn" else "eng_Latn"

        chunks = self._split_chunks(text)
        return "\n".join(self._translate_chunks(chunks, src_lang, tgt_lang))

    def _translate_chunks(self, chunks: list[str], src_lang: str, tgt_lang: str) -> list[str]:
        tok = self._tokenizer
        tok.src_lang = src_lang  # fast tokenizer 支持按次切换源语言
        batch_tokens = [tok.convert_ids_to_tokens(tok.encode(c)) for c in chunks]
        # 解码长度按输入长度自适应:生造词/乱码输入会让模型废话到 512 上限,
        # 在 CPU 上表现为"卡死";上限 64 步起步、256 步封顶,翻译足够。
        max_src = max(len(t) for t in batch_tokens)
        results = self._translator.translate_batch(
            batch_tokens,
            target_prefix=[[tgt_lang]] * len(chunks),
            beam_size=2,
            max_decoding_length=min(256, max(64, 4 * max_src)),
            repetition_penalty=1.2,
        )
        out = []
        for res in results:
            pieces = res.hypotheses[0][1:]  # 去掉开头的目标语言 token
            ids = tok.convert_tokens_to_ids(pieces)
            out.append(tok.decode(ids, skip_special_tokens=True).strip())
        return out

    def _split_chunks(self, text: str) -> list[str]:
        """按行/句子切分,贪心合并到不超过 MAX_SOURCE_TOKENS。"""
        tok = self._tokenizer
        pieces = re.split(r"(?<=[。!?.;\n])", text)
        pieces = [p for p in (p.strip() for p in pieces) if p]
        if not pieces:
            return [text]
        chunks: list[str] = []
        current = ""
        current_len = 0
        for piece in pieces:
            n = len(tok.encode(piece))
            if current and current_len + n > MAX_SOURCE_TOKENS:
                chunks.append(current)
                current, current_len = piece, n
            else:
                current = f"{current} {piece}".strip()
                current_len += n
        if current:
            chunks.append(current)
        return chunks


def detect_language(text: str) -> str:
    """字符集启发式源语言检测(够用即可,不追求语言学正确)。"""
    if re.search(r"[\uac00-\ud7af]", text):
        return "kor_Hang"
    if re.search(r"[\u3040-\u30ff]", text):  # 假名
        return "jpn_Jpan"
    if re.search(r"[\u4e00-\u9fff]", text):  # CJK 汉字(默认按简中处理)
        return "zho_Hans"
    if re.search(r"[\u0400-\u04ff]", text):
        return "rus_Latn"
    if re.search(r"[\u0600-\u06ff]", text):
        return "ara_Arab"
    return "eng_Latn"
