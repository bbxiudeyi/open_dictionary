"""线程池任务:把任意函数丢进 QThreadPool 执行,结果/异常回到主线程。

用法:
    run_in_thread(fn, on_done, on_error, *args, timeout_ms=30000)
on_done/on_error 在主线程执行。

实现要点:完成信号挂在**模块级长寿命分发器**上,而不是 QRunnable 自己。
QRunnable 结束后会被线程池自动销毁,其 Python 包装随即可能被 GC,
若排队中的信号事件还挂在该对象上就会被静默丢弃——表现为"翻译中"之后
永远没有结果(时好时坏的竞态)。
"""

from __future__ import annotations

import itertools
import logging
import threading
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

logger = logging.getLogger(__name__)


class _Dispatcher(QObject):
    """长寿命信号分发器(主线程)。"""

    finished = Signal(int, object)  # (task_id, result)
    error = Signal(int, str)  # (task_id, 错误摘要)


_dispatcher = _Dispatcher()
_callbacks: dict[int, tuple[Callable | None, Callable | None]] = {}
_seq = itertools.count(1)
_lock = threading.Lock()


def _dispatch(task_id: int, ok: bool, value: Any) -> None:
    with _lock:
        cbs = _callbacks.pop(task_id, None)
    if cbs is None:  # 已超时被清理
        return
    on_done, on_error = cbs
    try:
        if ok:
            if on_done is not None:
                on_done(value)
        elif on_error is not None:
            on_error(value)
    except Exception:
        logger.error("回调执行失败:\n%s", traceback.format_exc())


_dispatcher.finished.connect(lambda i, v: _dispatch(i, True, v))
_dispatcher.error.connect(lambda i, e: _dispatch(i, False, e))


class _Task(QRunnable):
    def __init__(self, fn: Callable, args: tuple, on_done, on_error) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        with _lock:
            self._id = next(_seq)
            _callbacks[self._id] = (on_done, on_error)

    def run(self) -> None:
        try:
            result = self._fn(*self._args)
        except Exception:
            detail = traceback.format_exc()
            logger.error("后台任务失败(task %d):\n%s", self._id, detail)
            _dispatcher.error.emit(self._id, detail.strip().splitlines()[-1])
        else:
            _dispatcher.finished.emit(self._id, result)


def run_in_thread(
    fn: Callable,
    on_done: Callable[[Any], None] | None,
    on_error: Callable[[str], None] | None,
    *args: Any,
    timeout_ms: int = 0,
) -> None:
    """后台执行 fn(*args);完成/异常经排队信号回到主线程。

    timeout_ms > 0 时,超时后调用 on_error(线程无法强杀,只是不再等它)。
    """
    task = _Task(fn, args, on_done, on_error)
    QThreadPool.globalInstance().start(task)
    if timeout_ms > 0:
        task_id = task._id

        def _timeout() -> None:
            with _lock:
                cbs = _callbacks.pop(task_id, None)
            if cbs is None:
                return
            logger.warning("后台任务 %d 超时(%dms),放弃等待", task_id, timeout_ms)
            on_err = cbs[1]
            if on_err is not None:
                on_err(f"任务超时({timeout_ms // 1000}s),可重试")

        QTimer.singleShot(timeout_ms, _timeout)
