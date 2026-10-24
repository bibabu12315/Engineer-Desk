"""
搜索对话框（UI 重制版）
iOS 卡片质感：圆角搜索框、橙色主操作、标签胶囊、无边框结果列表
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QWidget, QScrollArea, QFrame,
)

from src.database.db_manager import DatabaseManager
from src.ui import theme


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
        self.setMinimumSize(440, 500)
        self.setStyleSheet(theme.dialog_qss())

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        # 标题
        title = QLabel("搜索")
        title.setStyleSheet(
            f"font-size: 17px; font-weight: 650; letter-spacing: -0.3px;"
            f" color: {theme.LABEL}; background: transparent;"
        )
        layout.addWidget(title)

        # 搜索栏：圆角输入 + 橙色主按钮
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索标题、正文、草稿或标签...")
        self._search_input.setFixedHeight(34)
        self._search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search_input)

        search_btn = QPushButton("搜索")
        search_btn.setProperty("qss", "primary")
        search_btn.setFixedHeight(34)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # 标签快捷胶囊（横向滚动）
        self._tag_buttons_widget = QWidget()
        self._tag_buttons_widget.setStyleSheet("background: transparent;")
        self._tag_buttons_layout = QHBoxLayout(self._tag_buttons_widget)
        self._tag_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_buttons_layout.setSpacing(6)
        self._tag_scroll = QScrollArea()
        self._tag_scroll.setWidgetResizable(True)
        self._tag_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._tag_scroll.setFixedHeight(30)
        self._tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_scroll.setWidget(self._tag_buttons_widget)
        layout.addWidget(self._tag_scroll)

        # 结果统计
        self._result_count = QLabel("")
        self._result_count.setStyleSheet(
            f"color: {theme.SECONDARY}; font-size: 11px;"
        )
        layout.addWidget(self._result_count)

        # 结果列表：无边框卡片
        self._results_list = QListWidget()
        self._results_list.setStyleSheet(
            "QListWidget {"
            f" border: 0.5px solid {theme.SEPARATOR}; border-radius: 12px;"
            f" background: {theme.SURFACE}; padding: 4px; }}"
            "QListWidget::item {"
            f" border-radius: 8px; padding: 7px 10px; margin: 1px 2px; }}"
            f"QListWidget::item:hover {{ background: {theme.FILL}; }}"
            f"QListWidget::item:selected {{ background: {theme.BLUE_SOFT};"
            f" color: {theme.LABEL}; }}"
        )
        self._results_list.itemDoubleClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results_list, 1)

    def _refresh_tag_buttons(self) -> None:
        """刷新标签快捷胶囊"""
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
                "QPushButton { border: none; border-radius: 999px;"
                f" padding: 0 10px; font-size: 11px; font-weight: 500;"
                f" background: {theme.FILL}; color: {theme.SECONDARY}; }}"
                f"QPushButton:hover {{ background: {theme.FILL2}; color: {theme.LABEL}; }}"
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
            # 富文本内容先剥掉 HTML 标记再预览
            if "<" in content and ">" in content:
                import re
                content = re.sub(r"<[^>]+>", "", content)
            # 正文为空时回退显示草稿区内容（草稿可搜）
            if not content.strip() and "draft_content" in row.keys():
                draft = row["draft_content"] or ""
                if "<" in draft and ">" in draft:
                    import re
                    draft = re.sub(r"<[^>]+>", "", draft)
                if draft.strip():
                    content = f"[草稿] {draft}"
            # 截取前 60 个字作为预览
            preview = content[:60].replace("\n", " ") + ("..." if len(content) > 60 else "")

            item = QListWidgetItem(f"{date_str}  {title}\n{preview}")
            item.setData(Qt.ItemDataRole.UserRole, date_str)
            self._results_list.addItem(item)

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        """结果被双击"""
        date_str = item.data(Qt.ItemDataRole.UserRole)
        if date_str:
            self.result_selected.emit(date_str)
            self.accept()
