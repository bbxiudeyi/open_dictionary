# 开发指南

## 1. 环境要求

- Windows 10/11
- Python **3.10 – 3.12**(3.13 部分轮子可能未就绪)
- 磁盘:模型 ~600MB + 依赖 ~2GB

## 2. 初始化

```bash
cd D:/open-dictionary
python -m venv .venv
.venv\Scripts\activate          # Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
pip install -e ".[dev]"         # pytest / ruff / pyinstaller(可选)
```

## 3. 下载模型(首次必做)

```bash
# 默认走 hf-mirror.com(国内快)
python scripts/download_model.py

# 海外网络 / 镜像抽风时走官方源
python scripts/download_model.py --endpoint https://huggingface.co
```

下载内容:CTranslate2 int8 模型(~600MB)+ 分词器,存放在
`%APPDATA%/open-dictionary/models/nllb-200-distilled-600M-ct2-int8/`。

> 也可以先不下载直接 `python main.py`,首次按热键时会引导到设置页下载。

## 4. 运行与调试

```bash
python main.py          # 托盘启动
pytest                  # 快速单测(不含模型)
pytest -m slow          # 含模型的翻译用例(需先下载模型)
ruff check app tests    # 代码风格
```

日志:`%APPDATA%/open-dictionary/logs/app.log`(2MB 滚动 ×3)。
便携调试:设置 `OPEN_DICTIONARY_HOME=D:/od-data` 重定向全部数据。

默认热键:截图翻译 `Ctrl+Alt+T`,输入翻译 `Ctrl+Alt+Q`。

## 5. 打包发布

```bash
pip install pyinstaller
python scripts/build.py
# 产物:dist/OpenDictionary/OpenDictionary.exe(onedir)
```

- onedir 而非 onefile:启动快,杀毒误报率低。
- 模型**不打包**进安装包;用户首启下载(设置页有进度条与续传)。
- PyInstaller 产物偶尔被 Defender 误报,可对 exe 签名或引导用户加白名单。

## 6. 常见问题排查

| 症状 | 原因与处理 |
|---|---|
| 热键不响应 | 被其他软件占用(微信/QQ 截图等);换组合键。个别组合需管理员权限运行 |
| 框选区域与识别内容偏移 | DPI 换算问题,见 `ARCHITECTURE.md` §6.1;确认缩放设置并复现日志 |
| 加载模型报 `type must be string, but is null` | 模型目录缺 `config.json`(下载清单在 `constants.py`,勿删该项) |
| 下载 404 | HF 仓库文件名变更,核对 `app/constants.py` 中的 `NLLB_MODEL_FILES` |
| OCR 首次慢 | RapidOCR 首次加载模型 ~1s,属正常;之后常驻 |

## 7. 本地自行转换 NLLB 模型(备选方案)

当预转换仓库不可用时,自己从官方权重转换:

```bash
pip install "ctranslate2>=4" transformers sentencepiece torch
ct2-transformers-converter \
  --model facebook/nllb-200-distilled-600M \
  --output_dir %APPDATA%/open-dictionary/models/nllb-200-distilled-600M-ct2-int8 \
  --quantization int8
```

转换完把分词器四个文件(见 `constants.py` 的 `TOKENIZER_FILES`)放进
该目录的 `tokenizer/` 子目录即可。

## 8. 代码约定

- `app/core` 不得 import `PySide6.QtWidgets`(保持可独立测试);QtCore/QtGui
  里的非窗口类型(QImage/QRect)允许。
- 耗时操作一律 `run_in_thread`,主线程只画界面。
- 新增设置项:改 `AppSettings` → `settings_dialog` 加控件 → 文档 §5.2 同步。
- 提交信息用中文短句即可,不必 formal。
