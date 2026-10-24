"""
项目胶囊条（V2.0-c）
显示：图标 + 项目名 + 完成数/总数；按最近活跃度排序；超 6 个横向滚动
行为：点胶囊弹 ProjectDialog；「+ 项目」弹输入行创建（项目名 + 可选 emoji）
"""

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QScrollArea, QFrame, QLineEdit,
    QMenu, QMessageBox,
)

from src.database.db_manager import DatabaseManager
from src.widgets.project_dialog import ProjectDialog, days_since, STALE_DAYS


class ProjectCapsuleBar(QWidget):
    """底部项目胶囊条"""

    projects_changed = Signal()  # 项目数据发生变化（供外部刷新）

    _CAPSULE_STYLE = (
        "QPushButton {{ border: 0.5px solid {border}; border-radius: 10px;"
        " padding: 1px 10px; font-size: 11px; background: {bg}; color: {fg}; }}"
        "QPushButton:hover {{ background: {hover}; }}"
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db: DatabaseManager = DatabaseManager()
        self._dialog: ProjectDialog | None = None
        self._dialog_project_id: int | None = None

        self.setFixedHeight(30)
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
        self._inner = QWidget()
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

        add_btn = QPushButton("+ 项目")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(self._CAPSULE_STYLE.format(
            bg="transparent", fg="#888780", border="rgba(0,0,0,0.25)", hover="#fff"
        ))
        add_btn.setToolTip("新建项目（名称 + 可选 emoji 图标）")
        add_btn.clicked.connect(self._create_project)
        self._inner_layout.addWidget(add_btn)
        self._inner_layout.addStretch()

    def _build_capsule(self, project) -> QPushButton:
        label = f"{project['icon']} {project['name']} {project['done']}/{project['total']}".strip()
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("点击查看项目详情")

        days = days_since(project["sort_active_at"])
        if days >= STALE_DAYS:
            # × 天没碰：橙色提示
            btn.setStyleSheet(self._CAPSULE_STYLE.format(
                bg="#FAEEDA", fg="#854F0B", border="#E2C28C", hover="#F6E3C4"
            ))
            btn.setText(label + f" · {days}天没碰")
        elif project["total"] > 0 and project["done"] >= project["total"]:
            # 全部完成：绿色
            btn.setStyleSheet(self._CAPSULE_STYLE.format(
                bg="#E1F5EE", fg="#085041", border="#5DCAA5", hover="#d0efdd"
            ))
        else:
            btn.setStyleSheet(self._CAPSULE_STYLE.format(
                bg="rgba(0,0,0,0.04)", fg="#5F5E5A", border="rgba(0,0,0,0.15)",
                hover="rgba(255,255,255,0.9)"
            ))

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
            "QMenu { background: #ffffff; color: #333;"
            " border: 0.5px solid rgba(0,0,0,0.25); border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 4px 18px 4px 8px; border-radius: 4px; }"
            "QMenu::item:selected { background: #FDECEC; color: #c0392b; }"
        )
        del_act = menu.addAction(f"🗑 删除「{project_name}」")
        del_act.triggered.connect(
            lambda checked=False: self._delete_project(project_id, project_name)
        )
        menu.exec(capsule.mapToGlobal(capsule.rect().bottomLeft() + pos))

    def _delete_project(self, project_id: int, project_name: str) -> None:
        """删除项目（子项随级联一并删除），需确认"""
        answer = QMessageBox.question(
            self,
            "删除项目",
            f"确定删除「{project_name}」吗？\n项目备注与全部子项（含进度记录）将一并删除，且不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
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
        row = getattr(self, "_create_input", None)
        if row is not None:
            # 已打开：再次点击 = 收起（Hide 事件会在 eventFilter 里清理引用）
            row.close()
            return

        btn = self.sender()
        pos = btn.mapToGlobal(btn.rect().bottomLeft()) if btn else self.mapToGlobal(self.rect().bottomLeft())

        input_row = QLineEdit()
        input_row.setPlaceholderText("项目名（可加 emoji 图标，如：🎯 学习RT-Thread）")
        input_row.setWindowFlags(Qt.WindowType.Popup)
        input_row.setFixedSize(280, 30)
        input_row.setStyleSheet(
            "QLineEdit { border: 1px solid #BA7517; border-radius: 6px;"
            " font-size: 12px; padding: 4px 8px; background: #fff; }"
        )
        input_row.installEventFilter(self)

        def save() -> None:
            text = input_row.text().strip()
            name, icon = text, ""
            if text and not text[0].isalnum() and not "\u4e00" <= text[0] <= "\u9fff":
                # 首字符为 emoji 等符号时拆出来当图标
                icon, name = text[0], text[1:].strip()
            if name:
                self._db.create_project(name, icon)
                self.refresh()
                self.projects_changed.emit()
            self._close_create_input()

        input_row.returnPressed.connect(save)
        self._create_input = input_row
        input_row.show()
        input_row.move(pos.x(), pos.y() + 4)
        input_row.setFocus()

    def _close_create_input(self) -> None:
        """关闭并销毁新建项目输入行，清空引用"""
        row = getattr(self, "_create_input", None)
        self._create_input = None
        if row is not None:
            row.removeEventFilter(self)
            row.blockSignals(True)
            row.close()
            row.deleteLater()

    def eventFilter(self, obj, event) -> bool:
        """新建项目输入行：关闭（Esc / 点击外部 / 程序关闭）时清理引用

        Qt.Popup 旗标使输入行在点击外部时自动关闭并触发 Hide 事件——
        之前 bug 的根源是 Hide 后 _create_input 仍持有已销毁的引用，
        导致后续点击「+ 项目」直接 return，看起来毫无反应。
        """
        if obj is getattr(self, "_create_input", None):
            if event.type() == QEvent.Type.Hide:
                self._create_input = None
                obj.deleteLater()
            elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._close_create_input()
                return True
        return super().eventFilter(obj, event)
