# Open Dictionary

[中文说明](README_CN.md)

Snap-and-translate + vocabulary desktop tool for Windows. **Fully offline** — no API, no account, no telemetry.

## Features

- **Screenshot translate** — press the hotkey (default `Ctrl+Alt+T`), drag a region on screen, get OCR + translation in a popup right beside your selection. `ESC` to dismiss.
- **Input translate** — press `Ctrl+Alt+Q` (or single-click the tray icon) and type any text.
- **Vocabulary** — every translation is auto-saved to a local SQLite database: searchable, deletable, and exportable to CSV (Excel-friendly, UTF-8 BOM).
- **Local translation model** — NLLB-200-distilled-600M running via CTranslate2 (int8, ~600 MB, pure CPU).
- **UI language** — English / 中文, switchable in Settings.

## Quick Start (development)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\download_model.py   & :: first time only, ~600MB via hf-mirror
python main.py
```

## Packaging

```bat
python scripts\build.py
```

Produces a portable folder (`dist\OpenDictionary\`, ~470 MB) and an **Inno Setup installer** (`dist\OpenDictionarySetup-0.1.0.exe`, ~130 MB). The installer can optionally download the translation model during installation (default via hf-mirror.com, SHA-256 verified) and installs per-user without admin rights.

## User Data

Everything lives in `%APPDATA%\open-dictionary\`: `vocab.db` (vocabulary), `config.json` (settings), `models\` (NLLB). Back up that folder to migrate; uninstalling the app keeps it.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — layers, threading model, data flow, design decisions & pitfalls
- [Development Guide](docs/DEVELOPMENT.md) — setup, model download, tests, packaging, troubleshooting

## License

- **Code**: MIT — see [LICENSE](LICENSE).
- **Translation model** (NLLB-200-distilled-600M, downloaded at runtime, not bundled): CC-BY-NC 4.0 by Meta — **non-commercial use**. Commercial use requires a separate license from Meta or a different model.
- OCR models (PP-OCR via RapidOCR) and dependencies are distributed under their own licenses.

## Project Layout

```
main.py            entry point
app/core/          core services (hotkey / capture / OCR / NLLB / vocab / model store)
app/ui/            windows (tray / capture overlay / result popup / query / settings / vocab)
app/controllers/   translation flow state machine
app/workers/       thread-pool task runner
app/i18n.py        UI strings (zh / en)
installer/         Inno Setup script (in-install model download)
scripts/           model download / build
tests/             unit tests
```
