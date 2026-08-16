"""生词库:SQLite CRUD + 搜索。

线程模型:check_same_thread=False + 全局锁。写入频率极低(一次翻译一条),
读多写少,一把锁足够,不值得上单写线程队列。
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_text  TEXT NOT NULL,
    result_text  TEXT NOT NULL,
    src_lang     TEXT,
    tgt_lang     TEXT NOT NULL,
    origin       TEXT NOT NULL,   -- 'ocr' / 'input'
    created_at   TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_entries_source ON entries(source_text);
"""


class VocabStore:
    def __init__(self, db_path: Path | str) -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ---- 写 ----
    def add(
        self,
        source_text: str,
        result_text: str,
        src_lang: str,
        tgt_lang: str,
        origin: str,
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO entries(source_text, result_text, src_lang, tgt_lang, origin) "
                "VALUES(?, ?, ?, ?, ?)",
                (source_text, result_text, src_lang, tgt_lang, origin),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def delete(self, entry_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            self._conn.commit()

    # ---- 读 ----
    def search(self, keyword: str = "", limit: int = 200) -> list[dict]:
        sql = "SELECT * FROM entries"
        params: tuple = ()
        if keyword:
            sql += " WHERE source_text LIKE ? OR result_text LIKE ?"
            like = f"%{keyword}%"
            params = (like, like)
        sql += " ORDER BY id DESC LIMIT ?"
        params = params + (limit,)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        return int(row[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()
