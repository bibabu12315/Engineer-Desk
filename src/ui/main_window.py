"""
桌面便签主窗口
整合文本编辑器、Todo 列表，支持拖拽、缩放、字体/颜色/透明度设置
V1.1 新增：日历、历史导航、搜索、Tag、置顶切换、设置页面
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt, Signal, QPoint, QEvent, QRect
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QPushButton, QLabel, QFrame, QColorDialog,
    QComboBox, QSlider, QMenu, QWidgetAction,
)
from PySide6.QtGui import QFont, QColor, QAction, QMouseEvent

from src.database.db_manager import DatabaseManager
from src.services.auto_save_service import AutoSaveService
from src.services.config_manager import ConfigManager
from src.widgets.sticky_editor import StickyEditor
from src.widgets.todo_widget import TodoListWidget
from src.widgets.tag_bar import TagBar
from src.widgets.calendar_dialog import CalendarDialog
from src.widgets.search_dialog import SearchDialog
from src.ui.settings_dialog import SettingsDialog


class StickyNoteWindow(QMainWindow):
    """桌面便签主窗口"""

    close_requested = Signal()  # 请求关闭（隐藏到托盘）

    # 边缘拖拽缩放的检测宽度（像素）
    _RESIZE_MARGIN: int = 6

    def __init__(self) -> None:
        super().__init__()
        self._db: DatabaseManager = DatabaseManager()
        self._config: ConfigManager = ConfigManager()

        # 窗口属性：无边框、置顶、透明背景
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Engineer Desk")

        # 拖拽支持
        self._drag_pos: QPoint | None = None
        self._resizing: bool = False
        self._resize_edges: Qt.Edge = Qt.Edge(0)
        self._resize_origin: QPoint | None = None
        self._resize_geometry: QRect | None = None

        # 置顶状态
        self._is_pinned: bool = self._config.get("always_on_top", "1") == "1"

        # 自动保存服务
        self._auto_save: AutoSaveService = AutoSaveService(self)
        self._auto_save.set_callback(self._save_all)

        # 加载今日数据
        self._note = self._db.get_or_create_today_note()
        self._note_id: int = self._note["id"]

        # 对话框引用（避免重复创建）
        self._calendar_dialog: CalendarDialog | None = None
        self._search_dialog: SearchDialog | None = None
        self._settings_dialog: SettingsDialog | None = None

        self._init_ui()
        self._load_data()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _init_ui(self) -> None:
        """初始化界面"""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(
            self._RESIZE_MARGIN, self._RESIZE_MARGIN,
            self._RESIZE_MARGIN, self._RESIZE_MARGIN
        )
        main_layout.setSpacing(0)

        # 标题栏
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # 内容分割器（上：文本编辑器 + 标签栏，下：Todo 列表）
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)
        splitter.setChildrenCollapsible(False)

        # 编辑器容器（编辑器 + 标签栏）
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(2)

        self._editor = StickyEditor()
        self._editor.content_changed.connect(self._auto_save.trigger)
        editor_layout.addWidget(self._editor, 1)

        # 标签栏
        self._tag_bar = TagBar()
        self._tag_bar.tag_clicked.connect(self._on_tag_clicked)
        editor_layout.addWidget(self._tag_bar)

        splitter.addWidget(editor_container)

        # Todo 列表
        self._todo_list = TodoListWidget()
        self._todo_list.todo_changed.connect(self._auto_save.trigger)
        splitter.addWidget(self._todo_list)

        splitter.setSizes([300, 200])

        main_layout.addWidget(splitter, 1)

        # 底部工具栏
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        self.setMouseTracking(True)
        central.setMouseTracking(True)
        title_bar.setMouseTracking(True)
        splitter.setMouseTracking(True)
        toolbar.setMouseTracking(True)
        self._editor.setMouseTracking(True)
        self._todo_list.setMouseTracking(True)

    def _create_title_bar(self) -> QWidget:
        """创建标题栏（含置顶、导航、日历、搜索、设置按钮）"""
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setObjectName("titleBar")
        bar.setStyleSheet(
            "#titleBar { background: rgba(0,0,0,0.05); border-radius: 8px; }"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 2, 4, 2)
        layout.setSpacing(4)

        # 历史导航：前一天
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedSize(24, 24)
        self._prev_btn.setToolTip("前一天")
        self._prev_btn.setStyleSheet(self._nav_btn_style())
        self._prev_btn.clicked.connect(lambda: self._navigate_date("prev"))
        layout.addWidget(self._prev_btn)

        # 历史导航：后一天
        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedSize(24, 24)
        self._next_btn.setToolTip("后一天")
        self._next_btn.setStyleSheet(self._nav_btn_style())
        self._next_btn.clicked.connect(lambda: self._navigate_date("next"))
        layout.addWidget(self._next_btn)

        # 标题编辑框
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("标题")
        self._title_edit.setStyleSheet(
            "QLineEdit { border: none; background: transparent;"
            " font-weight: bold; font-size: 13px; }"
        )
        self._title_edit.textChanged.connect(self._auto_save.trigger)
        layout.addWidget(self._title_edit, 1)

        # 日期标签
        self._date_label = QLabel("")
        self._date_label.setStyleSheet("color: #aaa; font-size: 10px; padding: 0 4px;")
        layout.addWidget(self._date_label)

        # 搜索按钮
        self._search_btn = QPushButton("🔍")
        self._search_btn.setFixedSize(26, 26)
        self._search_btn.setToolTip("搜索")
        self._search_btn.setStyleSheet(self._icon_btn_style())
        self._search_btn.clicked.connect(self._open_search)
        layout.addWidget(self._search_btn)

        # 日历按钮
        self._cal_btn = QPushButton("📅")
        self._cal_btn.setFixedSize(26, 26)
        self._cal_btn.setToolTip("日历")
        self._cal_btn.setStyleSheet(self._icon_btn_style())
        self._cal_btn.clicked.connect(self._open_calendar)
        layout.addWidget(self._cal_btn)

        # 置顶切换按钮（便签钉）
        self._pin_btn = QPushButton("📌")
        self._pin_btn.setFixedSize(26, 26)
        self._pin_btn.setToolTip("切换窗口置顶")
        self._pin_btn.setStyleSheet(self._icon_btn_style())
        self._pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self._pin_btn)

        # 设置按钮
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(26, 26)
        self._settings_btn.setStyleSheet(self._icon_btn_style())
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("隐藏到托盘")
        close_btn.setStyleSheet(
            "QPushButton { border: none; font-size: 18px; color: #999; }"
            "QPushButton:hover { color: #e74c3c; }"
        )
        close_btn.clicked.connect(self.hide_to_tray)
        layout.addWidget(close_btn)

        return bar

    def _create_toolbar(self) -> QWidget:
        """创建底部工具栏"""
        bar = QWidget()
        bar.setFixedHeight(26)
        bar.setStyleSheet("background: rgba(0,0,0,0.03); border-radius: 0 0 8px 8px;")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)

        # 回到今天按钮
        today_btn = QPushButton("回到今天")
        today_btn.setFixedHeight(20)
        today_btn.setStyleSheet(
            "QPushButton { border: none; color: #888; font-size: 10px; }"
            "QPushButton:hover { color: #333; }"
        )
        today_btn.clicked.connect(self._goto_today)
        layout.addWidget(today_btn)

        # 顺延按钮
        self._carry_btn = QPushButton("⏩ 顺延未完成")
        self._carry_btn.setFixedHeight(20)
        self._carry_btn.setToolTip("将未完成的 Todo 复制到明天")
        self._carry_btn.setStyleSheet(
            "QPushButton { border: none; color: #888; font-size: 10px; }"
            "QPushButton:hover { color: #4a90d9; }"
        )
        self._carry_btn.clicked.connect(self._carry_over_todos)
        layout.addWidget(self._carry_btn)

        layout.addStretch()

        self._save_status = QLabel("")
        self._save_status.setStyleSheet("color: #4caf50; font-size: 10px;")
        layout.addWidget(self._save_status)

        return bar

    def _carry_over_todos(self) -> None:
        """将未完成的 Todo 顺延到明天"""
        from datetime import date, timedelta
        self._save_all()

        today = date.today()
        tomorrow = (today + timedelta(days=1)).isoformat()
        tomorrow_note = self._db.get_or_create_note_by_date(tomorrow)

        count = self._db.carry_over_todos(self._note_id, tomorrow_note["id"])
        if count > 0:
            self._save_status.setText(f"已顺延 {count} 项到明天")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self._save_status.setText(""))
        else:
            self._save_status.setText("没有未完成的任务")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self._save_status.setText(""))

    @staticmethod
    def _icon_btn_style() -> str:
        """通用图标按钮样式"""
        return (
            "QPushButton { border: none; font-size: 14px; color: #888; }"
            "QPushButton:hover { color: #333; }"
        )

    @staticmethod
    def _nav_btn_style() -> str:
        """导航按钮样式"""
        return (
            "QPushButton { border: none; font-size: 10px; color: #bbb; }"
            "QPushButton:hover { color: #555; }"
        )

    # ==================== 置顶切换 ====================

    def _toggle_pin(self) -> None:
        """切换窗口置顶状态"""
        self._is_pinned = not self._is_pinned
        self._update_window_flags()
        self._config.set("always_on_top", "1" if self._is_pinned else "0")

        # 更新按钮外观
        if self._is_pinned:
            self._pin_btn.setText("📌")
            self._pin_btn.setStyleSheet(
                "QPushButton { border: none; font-size: 14px; color: #e74c3c; }"
            )
        else:
            self._pin_btn.setText("📍")
            self._pin_btn.setStyleSheet(
                "QPushButton { border: none; font-size: 14px; color: #ccc; }"
            )

    def _update_window_flags(self) -> None:
        """更新窗口标志（置顶/非置顶）"""
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        if self._is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.show()  # 重新显示以应用 flags

    # ==================== 历史导航 ====================

    def _navigate_date(self, direction: str) -> None:
        """导航到前一天或后一天"""
        current_date = self._note["date"]
        adjacent = self._db.get_adjacent_note(current_date, direction)
        if adjacent is None:
            return

        # 保存当前数据
        self._save_all()

        # 切换到相邻日期
        self._note = adjacent
        self._note_id = adjacent["id"]
        self._load_note_data()
        self._update_nav_buttons()

    def _goto_today(self) -> None:
        """回到今天的便签"""
        self._save_all()
        self._note = self._db.get_or_create_today_note()
        self._note_id = self._note["id"]
        self._load_note_data()
        self._update_nav_buttons()

    def load_note_by_date(self, target_date: str) -> None:
        """加载指定日期的便签"""
        row = self._db.get_note_by_date(target_date)
        if row is None:
            return

        self._save_all()
        self._note = row
        self._note_id = row["id"]
        self._load_note_data()
        self._update_nav_buttons()

    def _load_note_data(self) -> None:
        """加载当前便签数据到界面（不改变窗口属性）"""
        note = self._note
        self._title_edit.setText(note["title"] or "")

        self._editor.blockSignals(True)
        self._editor.setPlainText(note["content"] or "")
        self._editor.blockSignals(False)

        # 更新标签
        self._tag_bar.set_tags(self._db.get_tags(self._note_id))

        # 更新日期标签
        self._date_label.setText(note["date"])

        # 加载 Todo
        self._todo_list.load(self._note_id)

    def _update_nav_buttons(self) -> None:
        """更新导航按钮状态"""
        current_date = self._note["date"]
        prev = self._db.get_adjacent_note(current_date, "prev")
        next_note = self._db.get_adjacent_note(current_date, "next")

        self._prev_btn.setEnabled(prev is not None)
        self._next_btn.setEnabled(next_note is not None)

    # ==================== 对话框 ====================

    def _open_calendar(self) -> None:
        """打开日历对话框"""
        if self._calendar_dialog is None:
            self._calendar_dialog = CalendarDialog(self)
            self._calendar_dialog.date_selected.connect(self.load_note_by_date)

        self._calendar_dialog._highlight_dates()
        self._calendar_dialog.show()
        self._calendar_dialog.raise_()
        self._calendar_dialog.activateWindow()

    def _open_search(self) -> None:
        """打开搜索对话框"""
        if self._search_dialog is None:
            self._search_dialog = SearchDialog(self)
            self._search_dialog.result_selected.connect(self.load_note_by_date)

        self._search_dialog._refresh_tag_buttons()
        self._search_dialog.show()
        self._search_dialog.raise_()
        self._search_dialog.activateWindow()

    def _open_settings(self) -> None:
        """打开设置对话框"""
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self)
            # 连接外观变更信号到主窗口方法
            self._settings_dialog.font_family_changed.connect(self._set_font_family)
            self._settings_dialog.font_size_changed.connect(self._set_font_size)
            self._settings_dialog.opacity_changed.connect(self._set_opacity)
            self._settings_dialog.bg_color_changed.connect(self._set_bg_color)

        # 打开前同步当前外观值
        self._settings_dialog.set_current_values(
            font_family=self._editor.font_family,
            font_size=self._editor.font_size,
            bg_color=self._extract_bg_color(),
            opacity=self.windowOpacity(),
        )
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_tag_clicked(self, tag: str) -> None:
        """标签被点击：在搜索对话框中搜索"""
        self._open_search()
        if self._search_dialog:
            self._search_dialog._search_by_tag(tag)

    # ==================== 外观设置 ====================

    def _show_settings_menu(self) -> None:
        """显示外观设置菜单（保留兼容）"""
        menu = QMenu(self)

        bg_action = menu.addAction("背景颜色...")
        bg_action.triggered.connect(self._pick_bg_color)

        opacity_menu = QMenu("透明度", menu)
        for pct in [100, 90, 80, 70, 60, 50]:
            action = opacity_menu.addAction(f"{pct}%")
            action.triggered.connect(
                lambda checked, v=pct: self._set_opacity(v / 100.0)
            )
        menu.addMenu(opacity_menu)

        font_menu = QMenu("字体", menu)
        for f in ["Microsoft YaHei", "SimSun", "KaiTi", "FangSong", "Consolas", "Arial"]:
            action = font_menu.addAction(f)
            action.triggered.connect(
                lambda checked, family=f: self._set_font_family(family)
            )
        menu.addMenu(font_menu)

        size_menu = QMenu("字号", menu)
        for s in [10, 11, 12, 14, 16, 18, 20]:
            action = size_menu.addAction(str(s))
            action.triggered.connect(
                lambda checked, size=s: self._set_font_size(size)
            )
        menu.addMenu(size_menu)

        menu.exec(self._settings_btn.mapToGlobal(
            self._settings_btn.rect().bottomLeft()
        ))

    def _pick_bg_color(self) -> None:
        """拾取背景色"""
        current = QColor(self._note["bg_color"])
        color = QColorDialog.getColor(current, self, "选择背景颜色")
        if color.isValid():
            self._set_bg_color(color.name())

    def _set_bg_color(self, color: str) -> None:
        self._apply_bg_style(color)
        self._auto_save.trigger()

    def _set_opacity(self, opacity: float) -> None:
        self.setWindowOpacity(opacity)
        self._auto_save.trigger()

    def _set_font_family(self, family: str) -> None:
        self._editor.set_font_family(family)
        self._auto_save.trigger()

    def _set_font_size(self, size: int) -> None:
        self._editor.set_font_size(size)
        self._auto_save.trigger()

    def _apply_bg_style(self, color: str) -> None:
        """应用背景样式到中央控件"""
        self.centralWidget().setStyleSheet(
            f"#centralWidget {{"
            f" background-color: {color};"
            f" border-radius: 10px;"
            f" }}"
        )

    # ==================== 数据加载与保存 ====================

    def _load_data(self) -> None:
        """从数据库加载数据到界面（首次启动）"""
        note = self._note
        self._title_edit.setText(note["title"] or "")

        self._editor.blockSignals(True)
        self._editor.set_font_family(note["font_family"] or "Microsoft YaHei")
        self._editor.set_font_size(note["font_size"] or 12)
        self._editor.setPlainText(note["content"] or "")
        self._editor.blockSignals(False)

        self._apply_bg_style(note["bg_color"] or "#FFFDE7")
        self.setWindowOpacity(note["opacity"] or 0.92)

        w = note["width"] or 400
        h = note["height"] or 500
        x = note["pos_x"] or 100
        y = note["pos_y"] or 100
        self.resize(w, h)
        self.move(x, y)

        # 标签
        self._tag_bar.set_tags(self._db.get_tags(self._note_id))

        # 日期
        self._date_label.setText(note["date"])

        # Todo
        self._todo_list.load(self._note_id)

        # 置顶状态
        self._update_pin_display()
        self._update_nav_buttons()

    def _update_pin_display(self) -> None:
        """更新置顶按钮的显示状态"""
        if self._is_pinned:
            self._pin_btn.setText("📌")
            self._pin_btn.setStyleSheet(
                "QPushButton { border: none; font-size: 14px; color: #e74c3c; }"
            )
        else:
            self._pin_btn.setText("📍")
            self._pin_btn.setStyleSheet(
                "QPushButton { border: none; font-size: 14px; color: #ccc; }"
            )

    def _save_all(self) -> None:
        """保存所有数据到数据库"""
        content = self._editor.get_plain_content()

        self._db.update_note(
            self._note_id,
            title=self._title_edit.text().strip(),
            content=content,
            font_family=self._editor.font_family,
            font_size=self._editor.font_size,
            bg_color=self._extract_bg_color(),
            opacity=self.windowOpacity(),
            width=self.width(),
            height=self.height(),
            pos_x=self.x(),
            pos_y=self.y(),
        )
        self._todo_list.save_all()

        # 提取并保存标签
        tags = self._db.set_tags(self._note_id, content)
        self._tag_bar.set_tags(tags)

        # 刷新缓存
        self._note = self._db.get_note_by_id(self._note_id)

        self._save_status.setText("✓ 已保存")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._save_status.setText(""))

    def _extract_bg_color(self) -> str:
        """从样式表中提取背景色"""
        style = self.centralWidget().styleSheet()
        import re
        match = re.search(r"background-color:\s*([^;]+)", style)
        return match.group(1).strip() if match else "#FFFDE7"

    # ==================== 窗口缩放辅助 ====================

    def _detect_resize_edge(self, pos: QPoint) -> Qt.Edge:
        """检测鼠标位置对应的窗口缩放边缘"""
        margin = self._RESIZE_MARGIN
        edges = Qt.Edge(0)
        if pos.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - margin:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= margin:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _cursor_for_edges(edges: Qt.Edge) -> Qt.CursorShape:
        """根据边缘返回对应的光标样式"""
        h = edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge)
        v = edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge)
        if h and v:
            if edges == (Qt.Edge.LeftEdge | Qt.Edge.TopEdge) or edges == (Qt.Edge.RightEdge | Qt.Edge.BottomEdge):
                return Qt.CursorShape.SizeFDiagCursor
            return Qt.CursorShape.SizeBDiagCursor
        if h:
            return Qt.CursorShape.SizeHorCursor
        if v:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def _begin_resize(self, global_pos: QPoint, edges: Qt.Edge) -> None:
        """开始边缘缩放"""
        self._resizing = True
        self._resize_edges = edges
        self._resize_origin = global_pos
        self._resize_geometry = self.geometry()

    def _update_resize(self, global_pos: QPoint) -> None:
        """更新边缘缩放"""
        if not self._resizing or self._resize_origin is None or self._resize_geometry is None:
            return

        delta = global_pos - self._resize_origin
        start = self._resize_geometry
        left = start.x()
        top = start.y()
        right = start.x() + start.width()
        bottom = start.y() + start.height()

        if self._resize_edges & Qt.Edge.LeftEdge:
            left += delta.x()
        if self._resize_edges & Qt.Edge.RightEdge:
            right += delta.x()
        if self._resize_edges & Qt.Edge.TopEdge:
            top += delta.y()
        if self._resize_edges & Qt.Edge.BottomEdge:
            bottom += delta.y()

        min_width = max(self.minimumWidth(), 260)
        min_height = max(self.minimumHeight(), 260)

        if right - left < min_width:
            if self._resize_edges & Qt.Edge.LeftEdge:
                left = right - min_width
            else:
                right = left + min_width

        if bottom - top < min_height:
            if self._resize_edges & Qt.Edge.TopEdge:
                top = bottom - min_height
            else:
                bottom = top + min_height

        self.setGeometry(left, top, right - left, bottom - top)

    def _finish_resize(self) -> None:
        """结束边缘缩放"""
        self._resizing = False
        self._resize_edges = Qt.Edge(0)
        self._resize_origin = None
        self._resize_geometry = None
        self._auto_save.trigger()

    def hide_to_tray(self) -> None:
        """隐藏到系统托盘"""
        self._save_all()
        self.hide()
        self.close_requested.emit()

    def show_window(self) -> None:
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    # ==================== 窗口拖拽与缩放事件 ====================

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._detect_resize_edge(self.mapFromGlobal(event.globalPosition().toPoint()))
            if edges != Qt.Edge(0):
                self._begin_resize(event.globalPosition().toPoint(), edges)
                return
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._resizing:
            self._update_resize(event.globalPosition().toPoint())
            return

        edges = self._detect_resize_edge(self.mapFromGlobal(event.globalPosition().toPoint()))
        self.setCursor(self._cursor_for_edges(edges))

        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        if self._resizing:
            self._finish_resize()
        else:
            self._auto_save.trigger()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event) -> bool:
        """捕获子控件上的边缘缩放鼠标事件"""
        if isinstance(obj, QWidget) and (obj is self or self.isAncestorOf(obj)):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    edges = self._detect_resize_edge(self.mapFromGlobal(event.globalPosition().toPoint()))
                    if edges != Qt.Edge(0):
                        self._begin_resize(event.globalPosition().toPoint(), edges)
                        return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._resizing:
                    self._update_resize(event.globalPosition().toPoint())
                    return True
                edges = self._detect_resize_edge(self.mapFromGlobal(event.globalPosition().toPoint()))
                self.setCursor(self._cursor_for_edges(edges))
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._resizing:
                    self._finish_resize()
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    return True

        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._auto_save.trigger()

    def closeEvent(self, event) -> None:
        self._save_all()
        self._db.close()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("EngineerDesk")
    app.setOrganizationName("EngineerDesk")

    window = StickyNoteWindow()
    window.show_window()

    sys.exit(app.exec())
