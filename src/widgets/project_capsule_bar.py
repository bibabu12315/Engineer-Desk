"""
项目胶囊条（V2.0-c）
显示：图标 + 项目名 + 完成数/总数；按最近活跃度排序；超 6 个横向滚动
行为：点胶囊弹 ProjectDialog；「+ 项目」弹输入行创建（项目名 + 可选 emoji）
"""

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QScrollArea, QFrame,
    QLineEdit, QMenu, QButtonGroup, QApplication, QLabel, QDialog,
)

from src.database.db_manager import DatabaseManager
from src.widgets.project_dialog import ProjectDialog, days_since, STALE_DAYS
from src.widgets.pill import PillButton
from src.ui.card_dialog import CardDialog
from src.ui import theme


class ProjectCapsuleBar(QWidget):
    """底部项目胶囊条"""

    projects_changed = Signal()  # 项目数据发生变化（供外部刷新）

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db: DatabaseManager = DatabaseManager()
        self._dialog: ProjectDialog | None = None
        self._dialog_project_id: int | None = None
        self._create_popup: QFrame | None = None
        self._create_input: QLineEdit | None = None
        self._create_button: QPushButton | None = None
        self._app_event_filter_installed = False

        self.setFixedHeight(30)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        root = QHBoxLayout(self)
        root.setContentsMargins(4, 0, 4, 2)
        root.setSpacing(4)

        # 横向滚动容器（超过 6 个胶囊时不设硬上限，横向滚动）
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(28)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        self._scroll.viewport().setStyleSheet("background: transparent;")
        self._scroll.viewport().setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )
        self._inner = QWidget()
        self._inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._inner.setStyleSheet("background: transparent;")
        self._inner_layout = QHBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(4)
        self._inner_layout.addStretch()
        self._scroll.setWidget(self._inner)
        root.addWidget(self._scroll, 1)

        self.refresh()

    # ==================== 刷新 ====================

    def refresh(self) -> None:
        """重绘所有胶囊"""
        while self._inner_layout.count():
            item = self._inner_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        projects = self._db.get_projects()
        for p in projects:
            self._inner_layout.addWidget(self._build_capsule(p))

        add_btn = PillButton("+ 项目", "ghost")
        add_btn.setObjectName("addProjectButton")
        add_btn.setToolTip("新建项目（名称 + 可选 emoji 图标）")
        add_btn.clicked.connect(self._create_project)
        self._inner_layout.addWidget(add_btn)
        self._create_button = add_btn
        self._inner_layout.addStretch()

    def _build_capsule(self, project) -> QPushButton:
        label = f"{project['icon']} {project['name']} {project['done']}/{project['total']}".strip()
        variant = "base"
        days = days_since(project["sort_active_at"])
        if days >= STALE_DAYS:
            variant = "warn"
            label += f" · {days}天没碰"
        elif project["total"] > 0 and project["done"] >= project["total"]:
            variant = "green"

        btn = PillButton(label, variant)
        btn.setToolTip("点击查看项目详情")

        btn.clicked.connect(
            lambda checked=False, pid=project["id"]: self._open_dialog(pid, btn)
        )

        # 右键菜单：删除项目
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, b=btn, pid=project["id"], name=project["name"]:
            self._show_project_menu(b, pid, name, pos)
        )
        return btn

    # ==================== 右键删除项目 ====================

    def _show_project_menu(self, capsule: QPushButton, project_id: int,
                           project_name: str, pos) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background: {theme.SURFACE}; color: {theme.LABEL};"
            f" border: 1px solid {theme.SEPARATOR}; border-radius: 10px;"
            " padding: 5px; }"
            f"QMenu::item {{ color: {theme.LABEL}; padding: 6px 12px;"
            " border-radius: 7px; }}"
            f"QMenu::item:selected {{ background: {theme.FILL}; }}"
        )
        del_act = menu.addAction(f"🗑 删除「{project_name}」")
        del_act.triggered.connect(
            lambda checked=False: self._delete_project(project_id, project_name)
        )
        menu.exec(capsule.mapToGlobal(capsule.rect().bottomLeft() + pos))

    def _delete_project(self, project_id: int, project_name: str) -> None:
        """删除项目（子项随级联一并删除），需确认"""
        dialog = CardDialog(self, title="删除项目", size=(420, 220))
        message = QLabel(
            f"确定删除「{project_name}」吗？\n"
            "项目备注与全部子项（含进度记录）将一并删除，且不可恢复。"
        )
        message.setWordWrap(True)
        dialog.body.addWidget(message)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancelDeleteButton")
        cancel_button.setProperty("qss", "secondary")
        cancel_button.clicked.connect(dialog.reject)
        actions.addWidget(cancel_button)

        delete_button = QPushButton("删除项目")
        delete_button.setObjectName("confirmDeleteButton")
        delete_button.setStyleSheet(
            f"QPushButton {{ color: #FFFFFF; background: {theme.RED};"
            " border: none; border-radius: 8px; padding: 5px 16px;"
            " font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #D93229; }"
        )
        delete_button.clicked.connect(dialog.accept)
        actions.addWidget(delete_button)
        dialog.body.addLayout(actions)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 若该项目弹窗开着，先关掉
        if self._dialog is not None and self._dialog_project_id == project_id:
            self._dialog.close()
            self._dialog.deleteLater()
            self._dialog = None
            self._dialog_project_id = None

        self._db.delete_project(project_id)
        self.refresh()
        self.projects_changed.emit()

    # ==================== 弹窗 ====================

    def _open_dialog(self, project_id: int, capsule: QPushButton) -> None:
        # 再次点按同一胶囊收起
        if (
            self._dialog is not None
            and self._dialog.isVisible()
            and self._dialog_project_id == project_id
        ):
            self._dialog.close()
            return

        if self._dialog is not None:
            self._dialog.deleteLater()

        dialog = ProjectDialog(self._db, project_id, self)
        dialog.destroyed.connect(self.refresh)
        self._dialog = dialog
        self._dialog_project_id = project_id
        # 在胶囊下方弹出
        pos = capsule.mapToGlobal(capsule.rect().bottomLeft())
        dialog.move(pos.x(), pos.y() + 4)
        dialog.show()

    # ==================== 新建项目 ====================

    def _create_project(self) -> None:
        """「+ 项目」胶囊：弹一行输入行（项目名 + 可选 emoji）

        - 输入行打开时再点一次「+ 项目」→ 收起
        - Esc / 点击输入行以外任意位置 → 收起（不创建）
        - 回车 → 创建
        """
        if self._create_popup is not None:
            # 已打开：再次点击 = 收起（Hide 事件会在 eventFilter 里清理引用）
            self._close_create_input()
            return

        btn = self.sender()
        pos = btn.mapToGlobal(btn.rect().bottomLeft()) if btn else self.mapToGlobal(self.rect().bottomLeft())

        popup = QFrame()
        popup.setObjectName("projectCreatePopup")
        popup.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        )
        popup.setFixedSize(220, 110)
        popup.setStyleSheet(
            f"QFrame#projectCreatePopup {{ background: {theme.SURFACE};"
            f" border: 1px solid {theme.SEPARATOR}; border-radius: 12px; }}"
        )
        popup.installEventFilter(self)
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(10, 8, 10, 8)
        popup_layout.setSpacing(6)

        selected_icon = ["🎯"]
        icon_options = (
            ("🎯", "目标"), ("⚡", "效率"), ("🚗", "出行"),
            ("📚", "学习"), ("💼", "工作"), ("🛠️", "工具"),
            ("💡", "灵感"), ("🏠", "生活"), ("🌱", "成长"),
            ("🎨", "创作"), ("🎵", "音乐"), ("📌", "其他"),
        )
        icon_group = QButtonGroup(popup)
        icon_group.setExclusive(True)

        for row_index in range(2):
            icon_row = QHBoxLayout()
            icon_row.setContentsMargins(0, 0, 0, 0)
            icon_row.setSpacing(4)
            for icon, description in icon_options[row_index * 6:(row_index + 1) * 6]:
                icon_button = QPushButton(icon)
                icon_button.setFixedSize(26, 26)
                icon_button.setCursor(Qt.CursorShape.PointingHandCursor)
                icon_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                icon_button.setCheckable(True)
                icon_button.setToolTip(description)
                icon_button.setStyleSheet(
                    "QPushButton { border: 1px solid transparent;"
                    " border-radius: 7px; background: transparent;"
                    " font-size: 15px; padding: 0; }"
                    f"QPushButton:hover {{ background: {theme.FILL}; }}"
                    f"QPushButton:checked {{ border-color: {theme.ACCENT};"
                    f" background: {theme.ACCENT_SOFT}; }}"
                )
                icon_group.addButton(icon_button)
                icon_button.setChecked(icon == selected_icon[0])
                icon_button.clicked.connect(
                    lambda checked, value=icon:
                    selected_icon.__setitem__(0, value) if checked else None
                )
                icon_row.addWidget(icon_button)
            icon_row.addStretch()
            popup_layout.addLayout(icon_row)

        input_row = QLineEdit()
        input_row.setPlaceholderText("输入项目名称")
        input_row.setStyleSheet(
            f"QLineEdit {{ color: {theme.LABEL}; background: {theme.BG};"
            f" border: 1px solid {theme.SEPARATOR}; border-radius: 7px;"
            f" font-size: 12px; padding: 3px 8px;"
            f" selection-background-color: {theme.BLUE};"
            " selection-color: #FFFFFF; }"
            f"QLineEdit:focus {{ border-color: {theme.ACCENT}; }}"
        )
        input_row.installEventFilter(self)
        popup_layout.addWidget(input_row)

        def save() -> None:
            text = input_row.text().strip()
            name, icon = text, selected_icon[0]
            for option in sorted(
                icon_options, key=lambda item: len(item[0]), reverse=True
            ):
                option_icon = option[0]
                if text.startswith(option_icon):
                    icon = option_icon
                    name = text[len(option_icon):].strip()
                    break
            else:
                if text and not text[0].isalnum() and not "\u4e00" <= text[0] <= "\u9fff":
                    icon, name = text[0], text[1:].strip()
            if name:
                self._db.create_project(name, icon)
                self.refresh()
                self.projects_changed.emit()
            self._close_create_input()

        input_row.returnPressed.connect(save)
        self._create_popup = popup
        self._create_input = input_row
        popup.move(pos.x(), pos.y() + 4)
        popup.show()
        popup.activateWindow()
        input_row.setFocus()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._app_event_filter_installed = True

    def _close_create_input(self) -> None:
        """关闭并销毁新建项目输入行，清空引用"""
        app = QApplication.instance()
        if app is not None and self._app_event_filter_installed:
            app.removeEventFilter(self)
        self._app_event_filter_installed = False
        popup = self._create_popup
        row = self._create_input
        self._create_popup = None
        self._create_input = None
        self._create_button = None
        if popup is not None:
            popup.removeEventFilter(self)
            popup.close()
            popup.deleteLater()
        if row is not None:
            row.removeEventFilter(self)
            row.blockSignals(True)

    def eventFilter(self, obj, event) -> bool:
        """新建项目弹窗：关闭（Esc / 点击外部 / 程序关闭）时清理引用

        工具窗口允许输入法正常组合输入；应用级事件过滤器补充点击外部关闭。
        """
        if (
            self._create_popup is not None
            and event.type() == QEvent.Type.MouseButtonPress
            and obj is not self._create_button
            and obj is not self._create_popup
            and not self._create_popup.isAncestorOf(obj)
        ):
            self._close_create_input()
            return False
        if obj is self._create_popup and event.type() == QEvent.Type.Hide:
            self._close_create_input()
        elif obj is self._create_input:
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._close_create_input()
                return True
        return super().eventFilter(obj, event)
