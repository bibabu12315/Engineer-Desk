"""
Todo 列表自定义控件
支持新建、删除、修改、勾选完成，显示今日完成数量
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
)
from PySide6.QtGui import QFont

from src.database.db_manager import DatabaseManager


class TodoItemWidget(QFrame):
    """单个 Todo 项控件"""

    changed = Signal()       # 内容变更信号
    remove_requested = Signal(object)  # 请求删除信号

    def __init__(
        self,
        todo_id: int,
        content: str = "",
        completed: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._todo_id: int = todo_id
        self._completed: bool = completed

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(6)

        # 完成勾选框
        self._checkbox: QCheckBox = QCheckBox()
        self._checkbox.setChecked(completed)
        self._checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self._checkbox)

        # 内容编辑框
        self._edit: QLineEdit = QLineEdit(content)
        self._edit.setPlaceholderText("输入待办事项...")
        self._edit.setStyleSheet(
            "QLineEdit { border: none; background: transparent; }"
        )
        self._edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._edit, 1)

        # 删除按钮
        self._delete_btn: QPushButton = QPushButton("×")
        self._delete_btn.setFixedSize(24, 24)
        self._delete_btn.setStyleSheet(
            "QPushButton { border: none; color: #999; font-size: 16px; }"
            "QPushButton:hover { color: #e74c3c; }"
        )
        self._delete_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self._delete_btn)

    @property
    def todo_id(self) -> int:
        return self._todo_id

    @property
    def is_completed(self) -> bool:
        return self._checkbox.isChecked()

    def text(self) -> str:
        return self._edit.text().strip()

    def set_completed(self, completed: bool) -> None:
        """设置完成状态（不触发信号）"""
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(completed)
        self._checkbox.blockSignals(False)

    def _on_toggle(self, checked: bool) -> None:
        """勾选状态切换"""
        self._completed = checked
        font = self._edit.font()
        font.setStrikeOut(checked)
        self._edit.setFont(font)
        if checked:
            self._edit.setStyleSheet(
                "QLineEdit { border: none; background: transparent; color: #999; }"
            )
        else:
            self._edit.setStyleSheet(
                "QLineEdit { border: none; background: transparent; }"
            )
        self.changed.emit()

    def _on_text_changed(self) -> None:
        """文本变更时发射信号"""
        self.changed.emit()


class TodoListWidget(QWidget):
    """Todo 列表控件，包含统计标签"""

    todo_changed = Signal()  # Todo 列表变更信号

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
        layout.setSpacing(4)

        # 头部：标题 + 统计
        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 4)

        title_label = QLabel("📋 Todo")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header.addWidget(title_label)

        header.addStretch()

        self._count_label = QLabel("完成: 0/0")
        self._count_label.setStyleSheet("color: #888;")
        header.addWidget(self._count_label)

        # 添加按钮
        add_btn = QPushButton("+ 新建")
        add_btn.setFixedHeight(26)
        add_btn.setStyleSheet(
            "QPushButton { border: 1px solid #ddd; border-radius: 4px;"
            " padding: 2px 10px; background: #f8f8f8; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        add_btn.clicked.connect(self._add_todo)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e0e0e0;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # 滚动区域
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
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
            )
            item.changed.connect(self._on_item_changed)
            item.remove_requested.connect(self._remove_item)
            self._items.append(item)
            # 插入到 stretch 之前
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
        item = TodoItemWidget(todo_id=row["id"])
        item.changed.connect(self._on_item_changed)
        item.remove_requested.connect(self._remove_item)
        self._items.append(item)
        self._list_layout.insertWidget(self._list_layout.count() - 1, item)
        self._update_count()

        # 自动聚焦到新创建的编辑框
        item.findChild(QLineEdit).setFocus()

    def _remove_item(self, item: TodoItemWidget) -> None:
        """删除 Todo 项"""
        self._db.delete_todo(item.todo_id)
        self._list_layout.removeWidget(item)
        self._items.remove(item)
        item.deleteLater()
        self._update_count()
        self.todo_changed.emit()

    def _on_item_changed(self) -> None:
        """Todo 项变更时保存到数据库"""
        for item in self._items:
            self._db.update_todo(
                item.todo_id,
                content=item.text(),
                completed=1 if item.is_completed else 0,
            )
        self._update_count()
        self.todo_changed.emit()

    def _update_count(self) -> None:
        """更新完成统计"""
        total = len(self._items)
        completed = sum(1 for item in self._items if item.is_completed)
        self._count_label.setText(f"完成: {completed}/{total}")

    def save_all(self) -> None:
        """保存所有 Todo 项到数据库"""
        self._on_item_changed()
