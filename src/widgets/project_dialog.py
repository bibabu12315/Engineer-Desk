"""
项目弹窗（V2.0-c · UI 设计稿第 4 节重制版）
点项目胶囊弹出：三态子项 / 两级备注 / 记一句进度 / ×天没碰
Qt.Popup 旗标：Esc 或点击弹窗外部自动关闭；弹窗内所有修改即时落库
视觉：iOS 质感 — 图标方块头部 / 4px 绿色进度条 / 圆角状态件 / 橙色主操作
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QProgressBar, QFrame, QScrollArea,
)

from src.database.db_manager import DatabaseManager
from src.ui import theme

# 子项三态（status: 0=未开始 1=进行中 2=完成）
STATUS_TEXT = {0: "", 1: "◐", 2: "✓"}
# ×天没碰 变橙的阈值
STALE_DAYS = 7


def days_since(date_str: str) -> int:
    """计算距今天数（date_str: 'YYYY-MM-DD HH:MM:SS' 或 'YYYY-MM-DD'）"""
    from datetime import datetime, date as _date
    if not date_str:
        return 0
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(date_str, fmt).date()
            return max(0, (_date.today() - d).days)
        except ValueError:
            continue
    return 0


def _date_short(date_str: str) -> str:
    """'YYYY-MM-DD...' → 'MM-DD'"""
    return date_str[5:10] if date_str and len(date_str) >= 10 else (date_str or "")


class ProjectDialog(QWidget):
    """项目详情弹窗（即时落库，关闭即生效）"""

    def __init__(self, db: DatabaseManager, project_id: int, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._project_id = project_id
        self._selected_item_id: int | None = None  # 「记一句进度」目标子项

        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFixedWidth(340)

        self._init_ui()
        self.refresh()

    # ==================== UI 构建 ====================

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        root.setSpacing(6)

        # 头部：图标方块 + 项目名/创建日期 + ×天没碰胶囊
        header = QHBoxLayout()
        header.setSpacing(10)
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(34, 34)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(
            f"font-size: 17px; background: {theme.ACCENT_SOFT}; border-radius: 10px;"
        )
        header.addWidget(self._icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self._name_label = QLabel()
        self._name_label.setStyleSheet(
            "font-size: 15px; font-weight: 650; letter-spacing: -0.2px;"
        )
        self._created_label = QLabel()
        self._created_label.setStyleSheet(f"font-size: 11px; color: {theme.SECONDARY};")
        title_col.addWidget(self._name_label)
        title_col.addWidget(self._created_label)
        header.addLayout(title_col, 1)

        self._stale_label = QLabel()
        self._stale_label.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {theme.WARN_DEEP};"
            f" background: {theme.WARN_SOFT}; border-radius: 999px; padding: 2px 8px;"
        )
        self._stale_label.hide()
        header.addWidget(self._stale_label)
        root.addLayout(header)

        # 进度条（4px，绿色）+ 统计行
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background: rgba(120,120,128,0.08); border: none; border-radius: 2px; }"
            "QProgressBar::chunk { background: #34C759; border-radius: 2px; }"
        )
        root.addWidget(self._progress_bar)
        self._progress_label = QLabel()
        self._progress_label.setStyleSheet(
            f"font-size: 11px; color: {theme.SECONDARY};"
        )
        root.addWidget(self._progress_label)

        # 子项滚动区
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._items_container = QWidget()
        self._items_container.setStyleSheet("background: transparent;")
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0, 6, 0, 6)
        self._items_layout.setSpacing(1)
        self._scroll.setWidget(self._items_container)
        root.addWidget(self._scroll, 1)

        # 项目备注（默认折叠）
        note_toggle = QPushButton("📝 项目备注 ▸")
        note_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        note_toggle.setFixedHeight(24)
        note_toggle.setStyleSheet(
            "QPushButton { border: none; border-radius: 7px; text-align: left;"
            f" font-size: 12px; color: {theme.SECONDARY}; padding: 0 4px; }}"
            f"QPushButton:hover {{ color: {theme.LABEL}; }}"
        )
        self._note_toggle_btn = note_toggle
        root.addWidget(note_toggle)

        self._project_note_edit = QLineEdit()
        self._project_note_edit.setPlaceholderText("目标、资料、阶段总结…")
        self._project_note_edit.setStyleSheet(
            "QLineEdit { border: 0.5px solid rgba(60,60,67,0.12); border-radius: 8px;"
            f" font-size: 12px; padding: 5px 8px; background: {theme.INPUT_BG}; }}"
            f"QLineEdit:focus {{ border: 1px solid {theme.ACCENT}; background: {theme.INPUT_BG}; }}"
        )
        self._project_note_edit.returnPressed.connect(self._save_project_note)
        self._project_note_edit.setVisible(False)
        root.addWidget(self._project_note_edit)

        # 底部操作行：主操作橙色实底，其余灰底
        actions = QHBoxLayout()
        actions.setSpacing(6)
        progress_btn = QPushButton("＋ 记一句进度")
        progress_btn.setToolTip("回车即存：更新选中子项的上次做到，并刷新项目活跃时间")
        progress_btn.setStyleSheet(
            f"QPushButton {{ border: none; border-radius: 9px; font-size: 11.5px;"
            f" font-weight: 600; background: {theme.ACCENT}; color: #FFF; }}"
            f"QPushButton:hover {{ background: #E88F00; }}"
        )
        progress_btn.setFixedHeight(30)
        progress_btn.clicked.connect(self._add_progress)
        item_btn = QPushButton("＋ 子项")
        item_btn.setStyleSheet(
            "QPushButton { border: none; border-radius: 9px; font-size: 11.5px;"
            f" background: rgba(120,120,128,0.08); color: {theme.LABEL}; }}"
            f"QPushButton:hover {{ background: rgba(120,120,128,0.16); }}"
        )
        item_btn.setFixedHeight(30)
        item_btn.clicked.connect(self._add_item)
        actions.addWidget(progress_btn, 2)
        actions.addWidget(item_btn, 1)
        root.addLayout(actions)

        # 记一句进度输入行（默认隐藏，回车即存）
        self._progress_input = QLineEdit()
        self._progress_input.setPlaceholderText("一句话进度，回车即存…")
        self._progress_input.setStyleSheet(
            "QLineEdit { border: 1px solid #FF9F0A; border-radius: 8px;"
            " font-size: 12px; padding: 5px 8px; background: " + theme.INPUT_BG + "; }"
        )
        self._progress_input.returnPressed.connect(self._save_progress)
        self._progress_input.setVisible(False)
        root.addWidget(self._progress_input)

        # 新建子项输入行（默认隐藏，回车即存）
        self._item_input = QLineEdit()
        self._item_input.setPlaceholderText("子项名称，回车添加…")
        self._item_input.setStyleSheet(
            "QLineEdit { border: 0.5px solid rgba(60,60,67,0.2); border-radius: 8px;"
            " font-size: 12px; padding: 5px 8px; background: " + theme.INPUT_BG + "; }"
        )
        self._item_input.returnPressed.connect(self._save_item)
        self._item_input.setVisible(False)
        root.addWidget(self._item_input)

    # ==================== 数据刷新 ====================

    def refresh(self) -> None:
        """从数据库重绘整个弹窗（修改即时落库后调用）"""
        project = self._db.get_project_by_id(self._project_id)
        if project is None:
            self.close()
            return

        self._icon_label.setText(project["icon"] or "📁")
        self._name_label.setText(project["name"])
        self._created_label.setText(f"创建于 {_date_short(project['created_at'])}")

        # × 天没碰（按项目最近活跃时间，≥7 天橙色，仅提示不打断）
        days = days_since(project["sort_active_at"])
        if days >= STALE_DAYS:
            self._stale_label.setText(f"{days} 天没碰")
            self._stale_label.show()
        else:
            self._stale_label.hide()

        # 进度
        total = project["total"]
        done = project["done"]
        self._progress_bar.setMaximum(max(total, 1))
        self._progress_bar.setValue(done)
        recent = _date_short(project["sort_active_at"])
        self._progress_label.setText(f"{done}/{total} 个子项完成 · 最近 {recent}")

        # 子项列表
        while self._items_layout.count():
            item = self._items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self._db.get_project_items(self._project_id)
        if not items:
            empty = QLabel("还没有子项，点「＋ 子项」创建")
            empty.setStyleSheet(
                f"color: {theme.TERTIARY}; font-size: 12px; padding: 8px 2px;"
            )
            self._items_layout.addWidget(empty)

        for row in items:
            self._items_layout.addWidget(self._build_item_row(row))

        # 项目备注回填（保持折叠状态）
        self._project_note_edit.setText(project["note"] or "")

    def _build_item_row(self, row) -> QWidget:
        """构建单条子项：圆角状态件 + 标题 + 上次进度 + ✎ 备注 + 备注小字"""
        item_id = row["id"]
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(2, 1, 2, 1)
        vbox.setSpacing(0)

        line = QHBoxLayout()
        line.setSpacing(9)

        selected = self._selected_item_id == item_id
        bg = theme.BLUE_SOFT if selected else "transparent"
        radius = "border-radius: 10px;" if selected else ""

        # 状态件：20px 圆角方块（空灰 / ◐ 橙 / ✓ 绿）
        status = row["status"]
        state_btn = QPushButton(STATUS_TEXT.get(status, ""))
        state_btn.setFixedSize(20, 20)
        state_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        state_style = {
            0: "background: rgba(120,120,128,0.08);",
            1: f"background: {theme.WARN_SOFT}; color: {theme.WARN_DEEP};",
            2: f"background: {theme.GREEN_SOFT}; color: {theme.GREEN_DEEP};",
        }[status]
        state_btn.setStyleSheet(
            f"QPushButton {{ border: none; font-size: 11px; font-weight: 700;"
            f" border-radius: 7px; {state_style} }}"
        )
        state_btn.setToolTip("点击循环切换：未开始 → 进行中 → 完成")
        state_btn.clicked.connect(lambda checked=False, i=item_id: self._cycle_status(i))

        done = status == 2
        title_label = QLabel(row["title"])
        title_label.setStyleSheet(
            f"font-size: 13px; background: {bg}; {radius} padding: 0 2px;"
            + ("color: #8E8E93; text-decoration: line-through;" if done else "")
        )
        title_label.mousePressEvent = lambda ev, i=item_id: self._select_item(i)

        note_btn = QPushButton("✎")
        note_btn.setFixedSize(20, 20)
        note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        note_btn.setStyleSheet(
            f"QPushButton {{ border: none; color: {theme.TERTIARY}; font-size: 12px;"
            f" border-radius: 6px; }}"
            f"QPushButton:hover {{ color: {theme.SECONDARY}; background: {theme.FILL}; }}"
        )
        note_btn.setToolTip("子项备注")
        note_btn.clicked.connect(lambda checked=False, i=item_id: self._edit_item_note(i))

        line.addWidget(state_btn)
        line.addWidget(title_label, 1)
        if row["last_progress"]:
            lp = QLabel("上次：" + row["last_progress"])
            lp.setStyleSheet(f"font-size: 10.5px; color: {theme.WARN_DEEP}; padding: 0 2px;")
            line.addWidget(lp)
        line.addWidget(note_btn)
        vbox.addLayout(line)

        # 子项备注：小字灰显在子项下方（与状态件对齐）
        if row["note"]:
            note_label = QLabel(row["note"])
            note_label.setWordWrap(True)
            note_label.setStyleSheet(
                f"font-size: 11px; color: {theme.SECONDARY}; padding-left: 31px;"
            )
            vbox.addWidget(note_label)

        return container

    # ==================== 交互动作 ====================

    def _select_item(self, item_id: int) -> None:
        """点选子项（记一句进度的目标），高亮显示"""
        self._selected_item_id = item_id
        self.refresh()

    def _cycle_status(self, item_id: int) -> None:
        """子项三态循环：0 → 1 → 2 → 0"""
        item = self._db.get_project_item(item_id)
        if item is None:
            return
        next_status = (item["status"] + 1) % 3
        self._db.update_project_item(item_id, status=next_status)
        self._db.touch_project(self._project_id)
        self.refresh()

    def _edit_item_note(self, item_id: int) -> None:
        """行内备注编辑：在子项下方插入输入框，回车保存（追加式，自动带日期）"""
        item = self._db.get_project_item(item_id)
        if item is None:
            return

        edit = QLineEdit()
        edit.setPlaceholderText("补充备注（回车保存，自动带日期）")
        edit.setStyleSheet(
            "QLineEdit { border: 0.5px solid rgba(60,60,67,0.2); border-radius: 7px;"
            " font-size: 11px; padding: 3px 6px; margin-left: 31px; }"
        )
        edit.returnPressed.connect(
            lambda: self._save_item_note(item_id, edit.text())
        )
        # Esc 取消：焦点被抢或弹窗关闭即销毁输入框
        edit.installEventFilter(self)
        self._inline_note_edit = edit
        # 找到该子项所在的容器行，把输入框插到它后面
        index = -1
        sender = self.sender()
        if sender is not None:
            container = sender.parentWidget()
            index = self._items_layout.indexOf(container) + 1
        self._items_layout.insertWidget(max(index, 0), edit)
        edit.setFocus()

    def eventFilter(self, obj, event) -> bool:
        # 行内备注输入框 Esc 取消
        if obj is getattr(self, "_inline_note_edit", None):
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._inline_note_edit.deleteLater()
                self._inline_note_edit = None
                return True
        return super().eventFilter(obj, event)

    def _save_item_note(self, item_id: int, text: str) -> None:
        from datetime import datetime
        text = text.strip()
        if not text:
            return
        # 追加式备注，自动带日期
        old = (self._db.get_project_item(item_id)["note"] or "").strip()
        new_line = f"（{datetime.now().strftime('%m-%d')}）{text}"
        note = f"{old}\n{new_line}" if old else new_line
        self._db.update_project_item(item_id, note=note)
        self._db.touch_project(self._project_id)
        self._inline_note_edit = None
        self.refresh()

    def _add_progress(self) -> None:
        """记一句进度：默认目标为选中的子项，否则第一个未完成子项"""
        if self._selected_item_id is None:
            for row in self._db.get_project_items(self._project_id):
                if row["status"] != 2:
                    self._selected_item_id = row["id"]
                    break
        if self._selected_item_id is None:
            self._progress_label.setText("先创建一个子项，再记进度")
            return
        self._progress_input.setVisible(True)
        self._progress_input.setFocus()

    def _save_progress(self) -> None:
        """回车即存：更新子项「上次做到」并刷新项目活跃时间"""
        from datetime import datetime
        text = self._progress_input.text().strip()
        self._progress_input.setVisible(False)
        self._progress_input.clear()
        if not text or self._selected_item_id is None:
            return
        stamped = f"（{datetime.now().strftime('%m-%d')}）{text}"
        self._db.update_project_item(self._selected_item_id, last_progress=stamped)
        self._db.touch_project(self._project_id)
        self.refresh()

    def _add_item(self) -> None:
        self._item_input.setVisible(True)
        self._item_input.setFocus()

    def _save_item(self) -> None:
        title = self._item_input.text().strip()
        self._item_input.setVisible(False)
        self._item_input.clear()
        if not title:
            return
        new_id = self._db.add_project_item(self._project_id, title)
        self._selected_item_id = new_id
        self.refresh()

    def _toggle_project_note(self) -> None:
        visible = not self._project_note_edit.isVisible()
        self._project_note_edit.setVisible(visible)
        self._note_toggle_btn.setText("📝 项目备注 ▾" if visible else "📝 项目备注 ▸")
        if visible:
            self._project_note_edit.setFocus()

    def _save_project_note(self) -> None:
        """项目备注回车保存（保留焦点，方便继续输入）"""
        self._db.update_project(self._project_id, note=self._project_note_edit.text())
        self._db.touch_project(self._project_id)
