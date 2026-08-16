"""模型文件管理:下载(断点续传 + 进度回调)、完整性校验。

不依赖 huggingface_hub,直接从 {endpoint}/{repo}/resolve/main/{file} 拉取,
endpoint 默认 hf-mirror.com,可在设置里改回官方源。
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

import requests

from app import constants

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]  # (0~1, 描述)


class DownloadError(RuntimeError):
    pass


class ModelStore:
    def __init__(self, base_dir: Path, endpoint: str | None = None) -> None:
        self._base = Path(base_dir)
        self._endpoint = (endpoint or constants.DEFAULT_HF_ENDPOINT).rstrip("/")

    @property
    def model_dir(self) -> Path:
        """CTranslate2 模型目录(含 model.bin 与分词器子目录)。"""
        return self._base / constants.NLLB_MODEL_DIRNAME

    @property
    def tokenizer_dir(self) -> Path:
        return self.model_dir / "tokenizer"

    def is_ready(self) -> bool:
        return not self.missing_files()

    def missing_files(self) -> list[str]:
        """校验文件存在性与最小体积,返回缺失项描述。"""
        missing: list[str] = []
        checks = [
            (self.model_dir, constants.NLLB_MODEL_REPO, constants.NLLB_MODEL_FILES),
            (self.tokenizer_dir, constants.TOKENIZER_REPO, constants.TOKENIZER_FILES),
        ]
        for directory, repo, files in checks:
            for name, min_bytes in files:
                path = directory / name
                if not path.exists() or path.stat().st_size < min_bytes:
                    missing.append(f"{repo}/{name}")
        return missing

    def download(
        self,
        on_progress: ProgressFn | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """下载全部缺失文件(已完整的跳过)。失败抛 DownloadError。"""
        jobs = [
            (self.model_dir, constants.NLLB_MODEL_REPO, constants.NLLB_MODEL_FILES),
            (self.tokenizer_dir, constants.TOKENIZER_REPO, constants.TOKENIZER_FILES),
        ]
        total_files = sum(len(f) for _, _, f in jobs)
        done_files = 0
        for directory, repo, files in jobs:
            directory.mkdir(parents=True, exist_ok=True)
            for name, min_bytes in files:
                target = directory / name
                if target.exists() and target.stat().st_size >= min_bytes:
                    done_files += 1
                    continue
                self._download_one(repo, name, target, min_bytes,
                                   on_progress, cancel_event,
                                   base=done_files, span=1, total=total_files)
                done_files += 1
        logger.info("模型文件全部就绪:%s", self.model_dir)

    def _download_one(
        self,
        repo: str,
        name: str,
        target: Path,
        min_bytes: int,
        on_progress: ProgressFn | None,
        cancel_event,
        base: int,
        span: int,
        total: int,
    ) -> None:
        url = f"{self._endpoint}/{repo}/resolve/main/{name}"
        part = target.with_suffix(target.suffix + ".part")
        headers = {}
        have = part.stat().st_size if part.exists() else 0
        if have:
            headers["Range"] = f"bytes={have}-"

        try:
            with requests.get(url, stream=True, timeout=30, headers=headers) as resp:
                if have and resp.status_code != 206:  # 服务器不支持续传,重来
                    have = 0
                    part.unlink(missing_ok=True)
                resp.raise_for_status()
                total_size = int(resp.headers.get("Content-Length", 0)) + have

                mode = "ab" if have else "wb"
                with open(part, mode) as fh:
                    downloaded = have
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        if cancel_event is not None and cancel_event.is_set():
                            raise DownloadError("已取消")
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if on_progress and total_size:
                            frac_in_file = downloaded / total_size
                            overall = (base + frac_in_file * span) / total
                            on_progress(
                                overall,
                                f"{name} {downloaded / 1e6:.0f}/{total_size / 1e6:.0f} MB",
                            )
        except requests.RequestException as exc:
            raise DownloadError(f"下载失败 {url}:{exc}") from exc

        if part.stat().st_size < min_bytes:
            part.unlink(missing_ok=True)
            raise DownloadError(f"文件不完整(小于预期):{name},请重试")
        part.replace(target)
