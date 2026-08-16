# Open Dictionary

[English](README.md)

划词翻译 + 生词本桌面工具(Windows)。**完全本地离线**——无 API、无账号、无遥测。

## 功能

- **截图翻译**:按热键(默认 `Ctrl+Alt+T`)→ 鼠标框选屏幕区域 → OCR 识别 → 译文浮窗显示在选区右侧,`ESC` 关闭
- **输入翻译**:按 `Ctrl+Alt+Q`(或单击托盘图标)打开输入窗口,回车翻译
- **生词本**:翻译结果自动存入本地 SQLite 词库,可搜索、可删除、可导出 CSV(Excel 直接打开不乱码)
- **本地翻译模型**:NLLB-200-distilled-600M,CTranslate2 int8 推理(约 600MB,纯 CPU)
- **界面语言**:中文 / English,设置里随时切换

## 快速开始(开发)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\download_model.py   & :: 仅首次,约 600MB,走 hf-mirror 镜像
python main.py
```

## 打包发布

```bat
python scripts\build.py
```

一条命令产出:绿色版目录(`dist\OpenDictionary\`,约 470MB)和 **Inno Setup 安装包**(`dist\OpenDictionarySetup-0.1.0.exe`,约 130MB)。安装包按用户安装、无需管理员权限,安装向导可选**立即下载翻译模型**(默认走 hf-mirror.com 国内镜像,自动 SHA-256 校验)。

## 用户数据

全部位于 `%APPDATA%\open-dictionary\`:`vocab.db`(生词本)、`config.json`(设置)、`models\`(NLLB 模型)。备份这个文件夹即可迁移;卸载程序不会删除用户数据。

## 文档

- [架构设计](docs/ARCHITECTURE.md) —— 分层、线程模型、数据流、设计决策与坑
- [开发指南](docs/DEVELOPMENT.md) —— 环境搭建、模型下载、测试、打包、排障

## 目录速览

```
main.py            入口
app/core/          核心服务(热键/截图/OCR/翻译/词库/模型下载)
app/ui/            界面(托盘/框选遮罩/结果浮窗/输入/设置/生词本)
app/controllers/   翻译流程状态机
app/workers/       线程池任务封装
app/i18n.py        界面文案(中/英)
installer/         Inno Setup 安装包脚本(含安装期模型下载)
scripts/           模型下载 / 打包
tests/             单元测试
```
