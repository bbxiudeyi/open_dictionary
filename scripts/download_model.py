"""CLI 预下载 NLLB 模型(调试 / 离线部署用)。

用法:
    python scripts/download_model.py                    # 默认 hf-mirror
    python scripts/download_model.py --endpoint https://huggingface.co
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import constants  # noqa: E402
from app.core.model_store import ModelStore  # noqa: E402
from app.paths import models_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="下载 Open Dictionary 翻译模型")
    parser.add_argument(
        "--endpoint",
        default=constants.DEFAULT_HF_ENDPOINT,
        help=f"HuggingFace 端点(默认 {constants.DEFAULT_HF_ENDPOINT})",
    )
    args = parser.parse_args()

    store = ModelStore(models_dir(), endpoint=args.endpoint)
    if store.is_ready():
        print("模型已就绪:", store.model_dir)
        return 0

    def on_progress(frac: float, detail: str) -> None:
        print(f"\r[{frac * 100:5.1f}%] {detail}", end="", flush=True)

    try:
        store.download(on_progress)
    except Exception as exc:
        print(f"\n下载失败:{exc}")
        return 1
    print("\n完成:", store.model_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
