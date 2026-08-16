"""生词本窗口:浏览 / 搜索 / 删除 / 导出历史词条。"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import i18n
from app.core.vocab import VocabStore


class VocabWindow(QWidget):
    def __init__(self, vocab: VocabStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("vocab_title"))
        self.resize(680, 420)
        self._vocab = vocab
        self._columns = [
            i18n.tr("col_time"), i18n.tr("col_source"),
            i18n.tr("col_result"), i18n.tr("col_origin"),
        ]

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(i18n.tr("vocab_search"))
        self.search_input.textChanged.connect(self.refresh)
        top.addWidget(self.search_input, 1)
        refresh_btn = QPushButton(i18n.tr("vocab_refresh"))
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        export_btn = QPushButton(i18n.tr("vocab_export"))
        export_btn.clicked.connect(self._choose_dir_and_export)
        top.addWidget(export_btn)
        layout.addLayout(top)

        self.table = QTableWidget(0, len(self._columns))
        self.table.setHorizontalHeaderLabels(self._columns)
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
        delete_action = menu.addAction(i18n.tr("vocab_delete"))
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == delete_action:
            self._vocab.delete(entry_id)
            self.refresh()

    # ---- 导出 ----
    def _choose_dir_and_export(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, i18n.tr("vocab_export"))
        if not directory:
            return  # 用户取消
        filename = f"open-dictionary-vocab-{datetime.now():%Y%m%d-%H%M%S}.csv"
        path = Path(directory) / filename
        try:
            count = self.export_to(path)
        except OSError as exc:
            QMessageBox.warning(self, i18n.tr("vocab_export"), i18n.tr("export_failed").format(exc))
            return
        QMessageBox.information(
            self, i18n.tr("vocab_export"), i18n.tr("export_done").format(count, path)
        )

    def export_to(self, path) -> int:
        """把当前搜索结果(无搜索 = 全部)导出为 UTF-8 BOM CSV,返回条数。

        utf-8-sig 让 Excel 双击打开时中文不乱码。
        """
        rows = self._vocab.search(self.search_input.text().strip(), limit=10**7)
        header = [
            i18n.tr("col_time"), i18n.tr("col_source"), i18n.tr("col_result"),
            i18n.tr("col_src_lang"), i18n.tr("col_tgt_lang"), i18n.tr("col_origin"),
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for r in rows:
                writer.writerow([
                    r["created_at"], r["source_text"], r["result_text"],
                    r["src_lang"] or "", r["tgt_lang"], r["origin"],
                ])
        return len(rows)

    def show_and_focus(self) -> None:
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
