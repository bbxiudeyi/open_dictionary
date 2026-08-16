# Open Dictionary 架构文档

> 划词翻译 + 生词本桌面工具。OCR 截图翻译 / 手动输入查询两种入口,
> 翻译引擎为本地离线的 NLLB-200-distilled-600M(CTranslate2 int8,纯 CPU)。

## 1. 总体架构

四层结构,依赖方向自上而下,`core` 层不依赖任何 UI:

```
┌──────────────────────────────────────────────────────┐
│ UI 层(PySide6,全部在主线程)                          │
│ tray / capture_overlay / result_popup                 │
│ query_window / settings_dialog / vocab_window         │
├──────────────────────────────────────────────────────┤
│ 控制层(流程编排,Qt 信号驱动)                          │
│ controllers/translate_flow.py:框选→OCR→翻译→浮窗→入库 │
├──────────────────────────────────────────────────────┤
│ 服务层(app/core,无 UI 依赖,可独立单测)              │
│ hotkey / capture / ocr / nllb / vocab / model_store   │
├──────────────────────────────────────────────────────┤
│ 资源层(%APPDATA%/open-dictionary/)                    │
│ config.json / vocab.db / logs/app.log / models/…      │
└──────────────────────────────────────────────────────┘
```

横切关注点:

- `app/workers`:基于 `QThreadPool` 的通用后台任务封装(`run_in_thread`),
  所有耗时操作(OCR、翻译、模型下载、模型预热)走这里。
- `app/settings`:数据模型(`AppSettings`)与持久化(`SettingsStore`)分离,
  变更通过 `changed` 信号广播(热键管理器监听后自动重注册)。

## 2. 模块职责

| 模块 | 职责 | 关键点 |
|---|---|---|
| `main.py` | 组装:服务 → 流程 → 托盘 → 热键 | `QLockFile` 单实例;`setQuitOnLastWindowClosed(False)` 托盘常驻 |
| `core/hotkey.py` | 全局热键注册/注销 | keyboard 库回调在其监听线程,**只 emit 信号**,不碰 UI |
| `core/capture.py` | mss 截图 + 逻辑/物理像素换算 | DPI 换算集中于此,别处不出现乘法 |
| `core/ocr.py` | RapidOCR 封装 + 行合并 | 惰性加载;QImage→ndarray(BGR) |
| `core/nllb.py` | CTranslate2 + NLLB 翻译 | 惰性单例;`auto` 源语言字符集启发;>450 token 分块 |
| `core/vocab.py` | SQLite 生词本 CRUD | `check_same_thread=False` + 锁;WAL |
| `core/model_store.py` | 模型下载/校验 | 断点续传(Range);最小体积校验;hf-mirror 可配 |
| `controllers/translate_flow.py` | 状态机 | 唯一知道"整个流程"的地方 |
| `ui/capture_overlay.py` | 冻结屏 + 框选 | 每屏一个遮罩窗口;选区从**冻结帧**裁剪(所见即所得) |
| `ui/result_popup.py` | 译文浮窗 | 定位:右→左→下;ESC 关闭 |
| `ui/query_window.py` | 输入翻译 | 监听 `flow.result_ready` |
| `ui/settings_dialog.py` | 设置 + 模型下载 UI | 下载在后台线程,进度回调进 UI |
| `ui/vocab_window.py` | 生词本浏览/搜索/删除 | 右键删除 |

## 3. 核心数据流

```
用户按热键(ctrl+alt+t)
  │ keyboard 监听线程回调 → HotkeyManager.triggered 信号(排队投递)
  ▼
TranslateFlow.start_capture()
  ├─ 模型未就绪? → status + model_missing 信号 → 打开设置下载
  ├─ CaptureSession.start():mss 冻结全部屏幕 → 每屏一个遮罩
  │     ESC → canceled → 会话清理,回到 idle
  ├─ 松开鼠标 → 选区(全局逻辑 QRect)
  │     → 物理像素换算 → 从冻结帧裁剪 QImage → 关闭全部遮罩
  ├─ run_in_thread(OCR.recognize)
  │     空文本 → 浮窗提示"未识别到文字",流程结束
  ├─ run_in_thread(NllbTranslator.translate)
  ├─ ResultPopup.show_near(选区右侧) + result_ready 信号
  └─ auto_save_vocab 开启 → VocabStore.add(origin="ocr")
  ESC 关闭浮窗 → 回到 idle,等待下一次热键
```

输入模式:`QueryWindow → flow.translate_text(text) → 翻译 → result_ready → 入库(origin="input")`。

## 4. 线程模型

| 线程 | 内容 | 约束 |
|---|---|---|
| Qt 主线程 | 全部窗口、遮罩、浮窗、设置 | 绝不做耗时操作 |
| keyboard 监听线程 | 热键回调 | 只 emit 信号 |
| QThreadPool | OCR / 翻译 / 下载 / 预热 | 通过 `run_in_thread`,结果经 QueuedConnection 回主线程 |
| (无其他常驻线程) | | |

CTranslate2 的 `Translator` 创建一次后线程安全;`translate_batch` 始终在
worker 线程调用,主线程永不加载模型。

## 5. 数据模型

### 5.1 词库 `vocab.db`(SQLite,WAL)

```sql
CREATE TABLE entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_text  TEXT NOT NULL,
    result_text  TEXT NOT NULL,
    src_lang     TEXT,             -- eng_Latn / zho_Hans / …(auto 已解析)
    tgt_lang     TEXT NOT NULL,
    origin       TEXT NOT NULL,    -- 'ocr' / 'input'
    created_at   TEXT DEFAULT (datetime('now','localtime'))
);
```

### 5.2 配置 `config.json`

```json
{
  "capture_hotkey": "ctrl+alt+t",
  "query_hotkey": "ctrl+alt+q",
  "target_lang": "zho_Hans",
  "source_lang": "auto",
  "auto_save_vocab": true,
  "hf_endpoint": "https://hf-mirror.com",
  "model_dir": ""
}
```

读写策略:tmp 文件 + 原子替换;未知字段忽略、缺失字段补默认(向前兼容);
损坏时备份为 `.bak` 并回退默认值。

### 5.3 目录布局

```
%APPDATA%/open-dictionary/
├── config.json
├── vocab.db
├── .lock                     # QLockFile 单实例
├── logs/app.log              # 2MB 滚动 x3
└── models/nllb-200-distilled-600M-ct2-int8/
    ├── model.bin             # ~600MB(int8)
    ├── shared_vocabulary.txt
    └── tokenizer/            # sentencepiece + tokenizer.json 等
```

环境变量 `OPEN_DICTIONARY_HOME` 可整体重定向(便携模式 / 测试)。

## 6. 关键设计决策与坑

1. **DPI 换算集中管理**:mss 是物理像素,Qt 是逻辑像素。所有换算在
   `capture.py`(`logical_to_physical` / `screen_physical_rect`),
   遮罩层只做"冻结帧裁剪"。高分屏 125%/150% 缩放是该类工具最常见的偏移 bug 来源。
2. **冻结帧而非实时截屏**:遮罩显示按下热键瞬间的截图,松手时也从冻结帧
   裁剪,避免选择期间屏幕内容变化导致"选的不对"。
3. **热键回调线程安全**:keyboard 库回调绝不能直接操作 QWidget;
   统一 emit Qt 信号(自动排队连接到主线程)。
4. **模型惰性加载 + 预热**:启动后 1.5s 在后台线程 `ensure_loaded`,
   首次翻译不再吃 1~2s 的加载延迟;模型未就绪时按热键会引导去设置页下载。
5. **单实例**:`QLockFile`,防止两个进程抢注热键。
6. **ESC 语义**:框选中 = 取消;浮窗 = 关闭(即需求中的"退出键清空")。
7. **同语种处理**:源语言检测结果 == 目标语言时,自动翻转
   (英→英改为英→中,其余改为→英),避免"翻译了个寂寞"。

## 7. 错误处理策略

- 后台任务异常:`run_in_thread` 捕获全部异常,取最后一行错误信息回主线程,
  通过托盘气泡展示;完整堆栈写 `logs/app.log`。
- 下载失败:保留 `.part` 文件,重试时 Range 续传;体积校验不过则删除重下。
- OCR 空结果:不弹错误,浮窗提示"未识别到文字"。

## 8. 路线图(未实现)

- 生词导出 CSV / Anki
- 生词去重与复习统计
- 结果浮窗钉住(pinned)模式
- Wayland/macOS 适配(当前按 Windows 键盘与截屏特性开发)
- OCR 置信度过滤与按行选择翻译
