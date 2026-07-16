"""
搜索对话框
支持全文搜索标题、正文内容和标签
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QScrollArea,
)
from PySide6.QtGui import QFont

from src.database.db_manager import DatabaseManager


class SearchDialog(QDialog):
    """搜索对话框"""

    result_selected = Signal(str)  # 选中结果的日期

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db: DatabaseManager = DatabaseManager()
        self.setWindowTitle("搜索")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(420, 480)

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 搜索栏
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索标题、正文或标签...")
        self._search_input.setStyleSheet(
            "QLineEdit { border: 1px solid #ddd; border-radius: 6px;"
            " padding: 6px 10px; font-size: 13px; }"
        )
        self._search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search_input)

        search_btn = QPushButton("搜索")
        search_btn.setStyleSheet(
            "QPushButton { border: 1px solid #4a90d9; border-radius: 6px;"
            " padding: 6px 14px; background: #4a90d9; color: white; }"
            "QPushButton:hover { background: #357abd; }"
        )
        search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # 标签快捷搜索
        self._tag_buttons_layout = QHBoxLayout()
        self._tag_buttons_layout.setSpacing(4)
        self._refresh_tag_buttons()
        layout.addLayout(self._tag_buttons_layout)

        # 结果列表
        self._result_count = QLabel("")
        self._result_count.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._result_count)

        self._results_list = QListWidget()
        self._results_list.setStyleSheet(
            "QListWidget { border: 1px solid #eee; border-radius: 6px; }"
        )
        self._results_list.itemDoubleClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results_list, 1)

    def _refresh_tag_buttons(self) -> None:
        """刷新标签快捷按钮"""
        # 清除旧按钮
        while self._tag_buttons_layout.count():
            item = self._tag_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self._db.get_all_tags()
        for tag in tags[:12]:  # 最多显示 12 个
            btn = QPushButton(f"#{tag}")
            btn.setFixedHeight(24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { border: 1px solid #ddd; border-radius: 10px;"
                " padding: 0 8px; font-size: 11px; background: #f8f8f8; }"
                "QPushButton:hover { background: #e8e8e8; }"
            )
            btn.clicked.connect(lambda checked, t=tag: self._search_by_tag(t))
            self._tag_buttons_layout.addWidget(btn)

        self._tag_buttons_layout.addStretch()

    def _do_search(self) -> None:
        """执行全文搜索"""
        query = self._search_input.text().strip()
        if not query:
            return

        results = self._db.search_notes(query)
        self._display_results(results)

    def _search_by_tag(self, tag: str) -> None:
        """按标签搜索"""
        self._search_input.setText(f"#{tag}")
        results = self._db.search_by_tag(tag)
        self._display_results(results)

    def _display_results(self, results) -> None:
        """显示搜索结果"""
        self._results_list.clear()
        self._result_count.setText(f"找到 {len(results)} 条结果")

        for row in results:
            date_str = row["date"]
            title = row["title"] or "(无标题)"
            content = row["content"] or ""
            # 截取前 60 个字作为预览
            preview = content[:60].replace("\n", " ") + ("..." if len(content) > 60 else "")

            text = f"{date_str}  {title}\n{preview}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, date_str)
            self._results_list.addItem(item)

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        """结果被双击"""
        date_str = item.data(Qt.ItemDataRole.UserRole)
        if date_str:
            self.result_selected.emit(date_str)
            self.accept()
