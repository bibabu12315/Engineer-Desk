"""
Todo 列表控件（UI 重制版）
支持新建、删除、修改、勾选完成，显示今日完成数量和任务持续天数
视觉：圆角自绘复选框（绿底白✓）、发丝线分隔、胶囊操作按钮、完成态灰字划线
"""

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
    QTextEdit, QPushButton, QLabel, QScrollArea, QFrame,
)
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QFontMetrics

from src.database.db_manager import DatabaseManager
from src.ui import theme


class RoundCheckBox(QCheckBox):
    """自绘复选框：iOS 风格圆角方块，选中绿底白✓"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(17, 17)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRect(1, 1, self.width() - 2, self.height() - 2)
        if self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.GREEN))
            p.drawRoundedRect(r, 5, 5)
            # 白色对勾
            pen = QPen(QColor("#FFFFFF"), 1.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            w = self.width()
            h = self.height()
            p.drawLine(int(w * 0.24), int(h * 0.52), int(w * 0.42), int(h * 0.70))
            p.drawLine(int(w * 0.42), int(h * 0.70), int(w * 0.76), int(h * 0.30))
        else:
            p.setPen(QPen(QColor(theme.TERTIARY), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 5, 5)
        p.end()


class TodoItemWidget(QFrame):
    """单个 Todo 项控件，显示持续天数"""

    changed = Signal()
    remove_requested = Signal(object)

    def __init__(
        self,
        todo_id: int,
        content: str = "",
        completed: bool = False,
        origin_date: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._todo_id: int = todo_id
        self._completed: bool = completed
        self._origin_date: str = origin_date
        self._db: DatabaseManager = DatabaseManager()

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(30)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy().Preferred,
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 4, 2)
        layout.setSpacing(8)

        # 完成勾选框（自绘圆角）
        self._checkbox: RoundCheckBox = RoundCheckBox()
        self._checkbox.setChecked(completed)
        self._checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self._checkbox, 0, Qt.AlignmentFlag.AlignTop)

        # 内容编辑区域
        self._edit: QTextEdit = QTextEdit()
        self._edit.setPlaceholderText("输入待办事项...")
        self._edit.setFrameShape(QTextEdit.Shape.NoFrame)
        self._edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._edit.setStyleSheet("QTextEdit { border: none; background: transparent; }")
        self._edit.setPlainText(content)
        self._edit.setAcceptRichText(False)
        self._edit.document().documentLayout().documentSizeChanged.connect(
            self._adjust_height
        )
        self._edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._edit, 1)

        # 持续天数标签
        days = self._db.calc_days_active(origin_date)
        self._days_label = QLabel()
        self._days_label.setStyleSheet(
            f"color: {theme.TERTIARY}; font-size: 10px; padding: 2px 4px;"
        )
        if days > 1:
            self._days_label.setText(f"{days}天")
            self._days_label.setToolTip(f"已持续 {days} 天")
        layout.addWidget(self._days_label, 0, Qt.AlignmentFlag.AlignTop)

        # 删除按钮
        self._delete_btn: QPushButton = QPushButton("×")
        self._delete_btn.setFixedSize(20, 20)
        self._delete_btn.setStyleSheet(
            "QPushButton { border: none; border-radius: 6px;"
            f" color: {theme.TERTIARY}; font-size: 14px; background: transparent; }}"
            f"QPushButton:hover {{ background: rgba(255,59,48,0.12); color: {theme.RED}; }}"
        )
        self._delete_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self._delete_btn, 0, Qt.AlignmentFlag.AlignTop)

        self._apply_done_style(completed, force=True)
        self._adjust_height()

    # ==================== 完成态样式 ====================

    def _apply_done_style(self, checked: bool, force: bool = False) -> None:
        """完成态：整段灰字 + 划线（QTextEdit 需用字符格式实现）"""
        if checked == self._completed and not force:
            return
        self._completed = checked
        cursor = self._edit.textCursor()
        cursor.select(cursor.SelectionType.Document)
        from PySide6.QtGui import QTextCharFormat
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(checked)
        fmt.setForeground(QColor(theme.SECONDARY if checked else theme.LABEL))
        cursor.mergeCharFormat(fmt)
        cursor.clearSelection()
        self._edit.setTextCursor(cursor)

    def _adjust_height(self) -> None:
        """根据内容自适应调整控件高度"""
        doc_h = self._edit.document().size().height()
        margins = self._edit.contentsMargins()
        total = int(doc_h + margins.top() + margins.bottom() + 8)
        self.setMinimumHeight(max(total, 30))
        self.setMaximumHeight(max(total, 300))

    @property
    def todo_id(self) -> int:
        return self._todo_id

    @property
    def is_completed(self) -> bool:
        return self._checkbox.isChecked()

    def text(self) -> str:
        return self._edit.toPlainText().strip()

    def set_completed(self, completed: bool) -> None:
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(completed)
        self._checkbox.blockSignals(False)
        self._apply_done_style(completed)

    def _on_toggle(self, checked: bool) -> None:
        self._apply_done_style(checked)
        self.changed.emit()

    def _on_text_changed(self) -> None:
        self.changed.emit()


class TodoListWidget(QWidget):
    """Todo 列表控件"""

    todo_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db: DatabaseManager = DatabaseManager()
        self._note_id: int = 0
        self._items: list[TodoItemWidget] = []

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(10, 2, 10, 2)

        # 小节标题：小写灰标，视觉退后
        title_label = QLabel("TODO")
        title_label.setStyleSheet(
            f"color: {theme.SECONDARY}; font-size: 10px; font-weight: 600;"
            " letter-spacing: 1px;"
        )
        header.addWidget(title_label)

        header.addStretch()

        self._count_label = QLabel("0/0")
        self._count_label.setStyleSheet(
            f"color: {theme.SECONDARY}; font-size: 11px;"
            " font-variant-numeric: tabular-nums;"
        )
        header.addWidget(self._count_label)

        add_btn = QPushButton("＋")
        add_btn.setFixedSize(24, 24)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setToolTip("新建待办")
        add_btn.setStyleSheet(
            "QPushButton { border: none; border-radius: 8px; font-size: 13px;"
            f" color: {theme.SECONDARY}; background: transparent; }}"
            f"QPushButton:hover {{ background: {theme.FILL}; color: {theme.LABEL}; }}"
        )
        add_btn.clicked.connect(self._add_todo)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # 发丝线分隔
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {theme.SEPARATOR}; border: none;")
        layout.addWidget(sep)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        self._scroll_area.setWidget(self._list_container)
        layout.addWidget(self._scroll_area, 1)

    def load(self, note_id: int) -> None:
        """从数据库加载 Todo 列表"""
        self.clear()
        self._note_id = note_id

        rows = self._db.get_todos(note_id)
        for row in rows:
            item = TodoItemWidget(
                todo_id=row["id"],
                content=row["content"],
                completed=bool(row["completed"]),
                origin_date=row["origin_date"] or "",
            )
            item.changed.connect(self._on_item_changed)
            item.remove_requested.connect(self._remove_item)
            self._items.append(item)
            self._list_layout.insertWidget(self._list_layout.count() - 1, item)

        self._update_count()

    def clear(self) -> None:
        """清空所有 Todo 项"""
        for item in self._items:
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def _add_todo(self) -> None:
        """新增 Todo 项"""
        if self._note_id == 0:
            return

        row = self._db.add_todo(self._note_id)
        item = TodoItemWidget(
            todo_id=row["id"],
            origin_date=row["origin_date"] or "",
        )
        item.changed.connect(self._on_item_changed)
        item.remove_requested.connect(self._remove_item)
        self._items.append(item)
        self._list_layout.insertWidget(self._list_layout.count() - 1, item)
        self._update_count()

        item.findChild(QTextEdit).setFocus()

    def _remove_item(self, item: TodoItemWidget) -> None:
        """删除 Todo 项"""
        self._db.delete_todo(item.todo_id)
        self._list_layout.removeWidget(item)
        self._items.remove(item)
        item.deleteLater()
        self._update_count()
        self.todo_changed.emit()

    def save_all(self) -> None:
        """保存所有 Todo 项"""
        for item in self._items:
            self._db.update_todo(
                item.todo_id,
                content=item.text(),
                completed=1 if item.is_completed else 0,
            )

    def _on_item_changed(self) -> None:
        """Todo 项变更时保存"""
        self.save_all()
        self._update_count()
        self.todo_changed.emit()

    def _update_count(self) -> None:
        """更新完成统计"""
        total = len(self._items)
        completed = sum(1 for item in self._items if item.is_completed)
        self._count_label.setText(f"完成 {completed}/{total}")
