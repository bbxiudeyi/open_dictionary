"""生词库测试:CRUD 与搜索。"""

from __future__ import annotations

from app.core.vocab import VocabStore


def make_store() -> VocabStore:
    return VocabStore(":memory:")


def test_add_and_search():
    store = make_store()
    store.add("hello", "你好", "eng_Latn", "zho_Hans", "ocr")
    store.add("world", "世界", "eng_Latn", "zho_Hans", "input")

    assert store.count() == 2
    rows = store.search("你好")
    assert len(rows) == 1 and rows[0]["source_text"] == "hello"

    # 按原文模糊搜
    rows = store.search("wor")
    assert len(rows) == 1 and rows[0]["result_text"] == "世界"


def test_recent_ordering():
    store = make_store()
    for i in range(5):
        store.add(f"w{i}", f"词{i}", "eng_Latn", "zho_Hans", "ocr")
    rows = store.search()
    assert rows[0]["source_text"] == "w4"  # 最新的在前


def test_delete():
    store = make_store()
    entry_id = store.add("solo", "单独", "eng_Latn", "zho_Hans", "ocr")
    store.delete(entry_id)
    assert store.count() == 0
