"""PyInstaller 打包脚本(Windows)。

产物:dist/OpenDictionary/(onedir,启动快,杀毒软件误报率低)
用法:python scripts/build.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXCLUDES = [
    "torch", "tkinter", "matplotlib", "pandas", "scipy",
    "IPython", "jedi", "pytest",
]


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "OpenDictionary",
        *[arg for ex in EXCLUDES for arg in ("--exclude-module", ex)],
        str(ROOT / "main.py"),
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
