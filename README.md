# Open Dictionary

划词翻译 + 生词本桌面工具(Windows)。完全本地离线,无 API、无遥测。

## 功能

- **截图翻译**:快捷键 → 鼠标框选 → OCR 识别 → 译文浮窗显示在选区右侧 → ESC 关闭
- **输入翻译**:快捷键或托盘打开输入窗口,回车翻译
- **生词本**:翻译结果自动入库,可搜索、删除
- **本地模型**:NLLB-200-distilled-600M(CTranslate2 int8,~600MB,纯 CPU)

## 快速开始

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_model.py   # 首次:下载模型(~600MB)
python main.py
```

默认快捷键:`Ctrl+Alt+T` 截图翻译,`Ctrl+Alt+Q` 输入翻译(可在设置中修改)。

## 文档

- [架构设计](docs/ARCHITECTURE.md) —— 分层、线程模型、数据流、设计决策
- [开发指南](docs/DEVELOPMENT.md) —— 环境、模型下载、测试、打包、排障

## 目录速览

```
main.py            入口
app/core/          核心服务(热键/截图/OCR/翻译/词库/模型下载)
app/ui/            界面(托盘/框选遮罩/结果浮窗/输入/设置/生词本)
app/controllers/   翻译流程状态机
app/workers/       线程池任务封装
scripts/           模型下载 / 打包
tests/             单元测试
```
