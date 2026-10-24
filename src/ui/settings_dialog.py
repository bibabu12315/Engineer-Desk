"""
设置页面对话框（对齐细化设计稿 §8）
卡片质感：无边框卡片、圆角输入/滑块/色块，选中色块橙描边
管理应用配置和应用外观：字体、字号、透明度、背景色、开机启动
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QGroupBox, QFormLayout, QSlider,
    QComboBox, QGridLayout, QFrame,
)

from src.services.config_manager import ConfigManager
from src.services.startup_manager import StartupManager
from src.ui import theme
from src.ui.card_dialog import CardDialog

# 预设背景色 — 参考主流笔记/文本类产品的柔和色调
PRESET_COLORS = [
    ("暖白", "#FDFBF7"),
    ("米黄", "#FBF6E8"),
    ("奶油", "#FDF6E3"),
    ("象牙", "#FFFFF0"),
    ("浅灰", "#F5F5F5"),
    ("雾灰", "#F0F0F0"),
    ("晨光", "#FFF8E7"),
    ("宣纸", "#F9F4E8"),
    ("竹青", "#F0F7ED"),
    ("湖蓝", "#F0F5FA"),
    ("藕粉", "#FBF0F0"),
    ("暗夜", "#2D2D2D"),
]


class SettingsDialog(CardDialog):
    """设置对话框"""

    # 外观变更信号
    font_family_changed = Signal(str)
    font_size_changed = Signal(int)
    opacity_changed = Signal(float)
    bg_color_changed = Signal(str)
    auto_start_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, title="设置", size=(452, 520))
        self._config: ConfigManager = ConfigManager()
        self._current_bg: str = "#FDFBF7"
        self._init_body()

    def _init_body(self) -> None:
        # ===== 外观 =====
        appearance_group = QGroupBox("外观")
        appearance_layout = QFormLayout(appearance_group)
        appearance_layout.setSpacing(8)

        # 字体
        self._font_combo = QComboBox()
        fonts = [
            "Microsoft YaHei", "SimSun", "KaiTi", "FangSong",
            "Consolas", "Courier New", "Arial",
        ]
        self._font_combo.addItems(fonts)
        self._font_combo.currentTextChanged.connect(
            lambda f: self.font_family_changed.emit(f)
        )
        appearance_layout.addRow("字体:", self._font_combo)

        # 字号
        self._font_size_combo = QComboBox()
        self._font_size_combo.addItems([str(s) for s in [10, 11, 12, 14, 16, 18, 20]])
        self._font_size_combo.setCurrentText("12")
        self._font_size_combo.currentTextChanged.connect(
            lambda s: self.font_size_changed.emit(int(s))
        )
        appearance_layout.addRow("字号:", self._font_size_combo)

        # 背景颜色 — 预设色块网格
        color_label = QLabel("背景色:")
        color_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        appearance_layout.addRow(color_label, self._create_color_grid())

        # 透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.setSpacing(8)
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(50, 100)
        self._opacity_slider.setValue(95)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self._opacity_slider, 1)

        self._opacity_label = QLabel("95%")
        self._opacity_label.setFixedWidth(36)
        self._opacity_label.setStyleSheet(
            f"color: {theme.SECONDARY}; font-size: 11px;"
            " font-variant-numeric: tabular-nums;"
        )
        opacity_layout.addWidget(self._opacity_label)
        appearance_layout.addRow("透明度:", opacity_layout)

        self.body.addWidget(appearance_group)

        # ===== 常规 =====
        general_group = QGroupBox("常规")
        general_layout = QVBoxLayout(general_group)

        self._auto_start_checkbox = QCheckBox("开机自动启动")
        auto_start_enabled = StartupManager.is_enabled()
        self._config.auto_start = auto_start_enabled
        self._auto_start_checkbox.setChecked(auto_start_enabled)
        self._auto_start_checkbox.toggled.connect(self._toggle_auto_start)
        general_layout.addWidget(self._auto_start_checkbox)

        self.body.addWidget(general_group)

        # ===== 关于 =====
        about_group = QGroupBox("关于")
        about_layout = QFormLayout(about_group)
        about_layout.addRow("应用名称:", QLabel("Engineer Desk"))
        about_layout.addRow("版本:", QLabel("V2.0"))
        about_layout.addRow("技术栈:", QLabel("Python 3.13 + PySide6 + SQLite"))
        about_layout.addRow("平台:", QLabel("Windows"))
        self.body.addWidget(about_group)

        self.body.addStretch()

    def _create_color_grid(self) -> QFrame:
        """预设颜色色块网格：checkable + autoExclusive，选中橙描边"""
        container = QFrame()
        container.setStyleSheet("QFrame { background: transparent; border: none; }")
        grid = QGridLayout(container)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, (name, hex_color) in enumerate(PRESET_COLORS):
            row = i // 6
            col = i % 6

            swatch = QPushButton()
            swatch.setFixedSize(34, 24)
            swatch.setCheckable(True)
            swatch.setAutoExclusive(True)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(name)
            # 暗色背景用白色描边区分
            border_color = "#5A5A5E" if hex_color == "#2D2D2D" else theme.SEPARATOR
            swatch.setStyleSheet(
                f"QPushButton {{"
                f" background-color: {hex_color};"
                f" border: 1px solid {border_color};"
                f" border-radius: 7px;"
                f" }}"
                f"QPushButton:hover {{ border: 1.5px solid {theme.SECONDARY}; }}"
                f"QPushButton:checked {{ border: 2px solid {theme.ACCENT}; }}"
            )
            swatch.toggled.connect(
                lambda checked, c=hex_color: self._select_color(checked, c)
            )
            grid.addWidget(swatch, row, col)

        return container

    def set_current_values(
        self,
        font_family: str,
        font_size: int,
        bg_color: str,
        opacity: float,
    ) -> None:
        """设置当前外观值（从主窗口同步）"""
        self._current_bg = bg_color

        # 字体
        idx = self._font_combo.findText(font_family)
        if idx >= 0:
            self._font_combo.blockSignals(True)
            self._font_combo.setCurrentIndex(idx)
            self._font_combo.blockSignals(False)

        # 字号
        self._font_size_combo.blockSignals(True)
        self._font_size_combo.setCurrentText(str(font_size))
        self._font_size_combo.blockSignals(False)

        # 透明度
        pct = int(opacity * 100)
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(pct)
        self._opacity_slider.blockSignals(False)
        self._opacity_label.setText(f"{pct}%")

    def _select_color(self, checked: bool, hex_color: str) -> None:
        """选择预设背景色（toggled：仅选中时发信号）"""
        if not checked:
            return
        self._current_bg = hex_color
        self.bg_color_changed.emit(hex_color)

    def _on_opacity_changed(self, value: int) -> None:
        """透明度滑块变更"""
        self._opacity_label.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

    def _toggle_auto_start(self, enabled: bool) -> None:
        """切换开机启动"""
        if enabled:
            StartupManager.enable()
        else:
            StartupManager.disable()
        self._config.auto_start = enabled
        self.auto_start_changed.emit(enabled)

    def set_auto_start_state(self, enabled: bool) -> None:
        """从托盘菜单同步开机启动状态，不重复写注册表"""
        self._auto_start_checkbox.blockSignals(True)
        self._auto_start_checkbox.setChecked(enabled)
        self._auto_start_checkbox.blockSignals(False)
