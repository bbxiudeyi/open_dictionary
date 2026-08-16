"""生词本窗口:浏览 / 搜索 / 删除历史词条。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.vocab import VocabStore


class VocabWindow(QWidget):
    COLUMNS = ["时间", "原文", "译文", "来源"]

    def __init__(self, vocab: VocabStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Open Dictionary — 生词本")
        self.resize(680, 420)
        self._vocab = vocab

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索原文 / 译文…")
        self.search_input.textChanged.connect(self.refresh)
        top.addWidget(self.search_input, 1)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 240)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        rows = self._vocab.search(self.search_input.text().strip())
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [row["created_at"], row["source_text"], row["result_text"], row["origin"]]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.table.setItem(i, j, item)

    def _context_menu(self, pos) -> None:
        item = self.table.itemAt(pos)
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        delete_action = menu.addAction("删除该词条")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == delete_action:
            self._vocab.delete(entry_id)
            self.refresh()

    def show_and_focus(self) -> None:
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
