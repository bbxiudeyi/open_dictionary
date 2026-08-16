"""打包脚本(Windows):PyInstaller 出程序目录 → Inno Setup 出安装包。

用法:
    python scripts/build.py                # 完整流程
    python scripts/build.py --no-installer # 只打 PyInstaller,不出安装包

产物:
    dist/OpenDictionary/                  程序目录(绿色版,可直接压缩分发)
    dist/OpenDictionarySetup-<版本>.exe    安装包(安装向导可选下载模型)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXCLUDES = [
    "torch", "tkinter", "matplotlib", "pandas", "scipy",
    "IPython", "jedi", "pytest",
]

ISCC_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    Path.home() / r"AppData\Local\Programs\Inno Setup 6\ISCC.exe",
]


def find_iscc() -> Path | None:
    for path in ISCC_CANDIDATES:
        if path.exists():
            return path
    return shutil.which("ISCC") and Path(shutil.which("ISCC")) or None


def build_app() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "OpenDictionary",
        # rapidocr 的 config.yaml 与内置 OCR 模型是包内数据文件,必须显式收集
        "--collect-data", "rapidocr_onnxruntime",
        *[arg for ex in EXCLUDES for arg in ("--exclude-module", ex)],
        str(ROOT / "main.py"),
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def build_installer() -> int:
    iscc = find_iscc()
    if iscc is None:
        print("[跳过] 未找到 Inno Setup(ISCC.exe),只产出程序目录。")
        print("       安装方法:winget install JRSoftware.InnoSetup")
        return 0
    iss = ROOT / "installer" / "open_dictionary.iss"
    print(f"\n编译安装包:{iscc} {iss}")
    return subprocess.call([str(iscc), str(iss)], cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="打包 Open Dictionary")
    parser.add_argument("--no-installer", action="store_true", help="跳过安装包编译")
    args = parser.parse_args()

    code = build_app()
    if code != 0:
        return code
    if args.no_installer:
        return 0
    return build_installer()


if __name__ == "__main__":
    sys.exit(main())
