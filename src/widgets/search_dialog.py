"""
搜索对话框（对齐细化设计稿 §6）
单行结果 = 橙色日期胶囊 + 命中片段（省略号截断）+ 来源标记；单击即跳转
顶部 Tag 胶囊横向排列，点一颗即按标签过滤
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QWidget, QScrollArea, QFrame,
)
from PySide6.QtGui import QFontMetrics

from src.database.db_manager import DatabaseManager
from src.ui import theme
from src.ui.card_dialog import CardDialog


def _strip_html(text: str) -> str:
    if text and "<" in text and ">" in text:
        import re
        return re.sub(r"<[^>]+>", "", text)
    return text or ""


class SearchDialog(CardDialog):
    """搜索对话框"""

    result_selected = Signal(str)  # 选中结果的日期

    def __init__(self, parent=None) -> None:
        super().__init__(parent, title="搜索", size=(472, 540))
        self._db: DatabaseManager = DatabaseManager()
        self._query: str = ""
        self._init_body()
        self._refresh_tag_buttons()

    def _init_body(self) -> None:
        # 搜索栏：圆角输入 + 橙色主按钮
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索标题与正文…")
        self._search_input.setFixedHeight(32)
        self._search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search_input, 1)

        search_btn = QPushButton("搜索")
        search_btn.setProperty("qss", "primary")
        search_btn.setFixedHeight(32)
        search_btn.setFixedWidth(64)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(search_btn)
        self.body.addLayout(search_layout)

        # 标签快捷胶囊（横向滚动，点一颗即过滤）
        self._tag_buttons_widget = QWidget()
        self._tag_buttons_widget.setStyleSheet("background: transparent;")
        self._tag_buttons_layout = QHBoxLayout(self._tag_buttons_widget)
        self._tag_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_buttons_layout.setSpacing(6)
        self._tag_scroll = QScrollArea()
        self._tag_scroll.setWidgetResizable(True)
        self._tag_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._tag_scroll.setFixedHeight(26)
        self._tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_scroll.setWidget(self._tag_buttons_widget)
        self.body.addWidget(self._tag_scroll)

        # 结果列表：单行式结果（设计稿 §6）
        self._results_list = QListWidget()
        self._results_list.setStyleSheet(
            "QListWidget {"
            f" border: none; background: transparent; padding: 0; }}"
            "QListWidget::item { border: none; }"
        )
        self._results_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._results_list.itemClicked.connect(self._on_result_clicked)
        self.body.addWidget(self._results_list, 1)

        # 结果统计
        self._result_count = QLabel("")
        self._result_count.setStyleSheet(
            f"color: {theme.TERTIARY}; font-size: 11px;"
        )
        self.body.addWidget(self._result_count)

    # ==================== 输入区 ====================

    def _refresh_tag_buttons(self) -> None:
        """刷新标签快捷胶囊"""
        while self._tag_buttons_layout.count():
            item = self._tag_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self._db.get_all_tags()
        for tag in tags[:12]:  # 最多显示 12 个
            btn = QPushButton(f"#{tag}")
            btn.setFixedHeight(22)
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

    # ==================== 搜索 ====================

    def _do_search(self) -> None:
        query = self._search_input.text().strip()
        if not query:
            return
        self._query = query
        self._display_results(self._db.search_notes(query))

    def _search_by_tag(self, tag: str) -> None:
        self._search_input.setText(f"#{tag}")
        self._query = ""
        self._display_results(self._db.search_by_tag(tag), source="标签")

    # ==================== 结果渲染 ====================

    @staticmethod
    def _format_date_chip(date_str: str) -> str:
        """YYYY-MM-DD → MM-DD 周X"""
        from datetime import datetime
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            return f"{d.strftime('%m-%d')} {['周一','周二','周三','周四','周五','周六','周日'][d.weekday()]}"
        except (ValueError, TypeError):
            return date_str or ""

    def _match_source(self, row) -> str:
        """判断命中来源：标签 / 标题 / 草稿 / 正文"""
        if not self._query:
            return ""
        q = self._query.lstrip("#")
        if q and q in (row["title"] or ""):
            return "标题"
        draft = _strip_html(row["draft_content"] if "draft_content" in row.keys() else "")
        if draft and self._query.lower() in draft.lower():
            return "草稿"
        content = _strip_html(row["content"] or "")
        if content and self._query.lower() in content.lower():
            return "正文"
        return "标签"

    def _build_row(self, row) -> tuple[QWidget, str]:
        """单行结果：日期胶囊 + 命中片段 + 来源标记"""
        date_str = row["date"]
        content = _strip_html(row["content"] or "")
        if not content.strip():
            draft = _strip_html(row["draft_content"] if "draft_content" in row.keys() else "")
            if draft.strip():
                content = draft
        snippet = " ".join(content.split())[:80]
        fm = QFontMetrics(self.font())
        snippet = fm.elidedText(snippet, Qt.TextElideMode.ElideRight, 240)

        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row_widget)
        h.setContentsMargins(2, 6, 2, 6)
        h.setSpacing(10)

        chip = QLabel(self._format_date_chip(date_str))
        chip.setStyleSheet(
            f"QLabel {{ color: {theme.WARN_DEEP}; background: {theme.ACCENT_SOFT};"
            " border-radius: 999px; padding: 1px 9px; font-size: 10.5px;"
            " font-variant-numeric: tabular-nums; }}"
        )
        h.addWidget(chip)

        snippet_label = QLabel(snippet)
        snippet_label.setStyleSheet(f"color: {theme.LABEL}; font-size: 12.5px; background: transparent;")
        h.addWidget(snippet_label, 1)

        source = self._match_source(row)
        if source:
            src_label = QLabel(source)
            src_label.setStyleSheet(
                f"color: {theme.TERTIARY}; font-size: 10.5px; background: transparent;"
            )
            h.addWidget(src_label)

        return row_widget, date_str

    def _display_results(self, results, source: str | None = None) -> None:
        self._results_list.clear()
        self._result_count.setText(f"找到 {len(results)} 条结果" if self._query or source else "")
        for row in results:
            row_widget, date_str = self._build_row(row)
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, date_str)
            self._results_list.addItem(item)
            self._results_list.setItemWidget(item, row_widget)

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        """单击结果行即跳转"""
        date_str = item.data(Qt.ItemDataRole.UserRole)
        if date_str:
            self.result_selected.emit(date_str)
            self.accept()
