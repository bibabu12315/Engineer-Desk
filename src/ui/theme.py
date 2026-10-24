"""
UI 设计令牌（Design Tokens）— 固定浅色主题
依据 docs/EngineerDesk-ui-redesign.html：
- 强调色只保留一种（iOS Orange），其余灰阶收敛为 Label/Secondary/Tertiary 三档
- 0.5px 发丝线替代边框；窗口 18 / 面板 12 / 按钮 8 / 胶囊 999 圆角
- 所有 QSS 都从这里取值，禁止散落硬编码色值

main.py 启动时调用 init(app)，始终使用设计稿中的浅色主题。
"""

from PySide6.QtGui import QColor, QPalette

# 便签底色：固定暖纸白（用户自定义色不覆盖）
PAPER_LIGHT = "#FFFDF8"
THEME_DEFAULT_BGS = {PAPER_LIGHT, "#1F1F21", "#FFFDE7", "#FDFBF7"}

BG = PAPER_LIGHT
LABEL = "#1C1C1E"
SECONDARY = "#8E8E93"
TERTIARY = "#C7C7CC"
SEPARATOR = "rgba(60,60,67,0.12)"
FILL = "rgba(120,120,128,0.08)"
FILL2 = "rgba(120,120,128,0.16)"
ACCENT = "#FF9F0A"
ACCENT_SOFT = "#FFF4E0"
ACCENT_HOVER = "#E88F00"
GREEN = "#34C759"
GREEN_SOFT = "#E8F8EE"
GREEN_DEEP = "#1B7F3B"
WARN_SOFT = "#FFF0DC"
WARN_DEEP = "#B26A00"
BLUE = "#007AFF"
BLUE_SOFT = "#F0F6FF"
RED = "#FF3B30"
INPUT_BG = "#FFFFFF"
SURFACE = "#FFFFFF"
PANE_BG = "#FBF9F2"
DRAFT_BG = "#F4F3EE"

FONT_STACK = '"Microsoft YaHei", "PingFang SC", sans-serif'


def init(app) -> None:
    """固定应用到设计稿定义的浅色调色板和控件样式"""
    app.setStyle("Fusion")
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: BG,
        QPalette.ColorRole.WindowText: LABEL,
        QPalette.ColorRole.Base: SURFACE,
        QPalette.ColorRole.AlternateBase: FILL,
        QPalette.ColorRole.ToolTipBase: LABEL,
        QPalette.ColorRole.ToolTipText: BG,
        QPalette.ColorRole.Text: LABEL,
        QPalette.ColorRole.Button: FILL,
        QPalette.ColorRole.ButtonText: LABEL,
        QPalette.ColorRole.BrightText: RED,
        QPalette.ColorRole.Highlight: BLUE,
        QPalette.ColorRole.HighlightedText: "#FFFFFF",
        QPalette.ColorRole.Link: BLUE,
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(app_qss())


def note_paper(user_bg: str) -> str:
    """决定便签内容区底色：
    - 用户自定义过颜色（不在默认色集合里）→ 原样保留
    - 默认色 / 旧默认色 → 使用设计稿的浅色纸面
    """
    if user_bg and user_bg not in THEME_DEFAULT_BGS:
        return user_bg
    return PAPER_LIGHT


# ==================== 全局 QSS ====================

def app_qss() -> str:
    """应用级 QSS：滚动条、菜单、ToolTip、输入光标等通用控件一次到位"""
    return f"""
    QWidget {{ font-family: {FONT_STACK}; color: {LABEL}; }}
    QTextEdit {{ color: {LABEL}; }}
    QLineEdit {{
        color: {LABEL}; selection-background-color: {BLUE};
        selection-color: #FFFFFF;
    }}
    QToolTip {{
        background: {LABEL}; color: {BG}; border: none;
        border-radius: 6px; padding: 4px 8px; font-size: 11px;
    }}
    QMenu {{
        background: {SURFACE}; color: {LABEL};
        border: 0.5px solid {SEPARATOR}; border-radius: 10px; padding: 5px;
    }}
    QMenu::item {{ padding: 5px 20px 5px 10px; border-radius: 7px; font-size: 12px; }}
    QMenu::item:selected {{ background: {FILL}; }}
    QMenu::separator {{ height: 0.5px; background: {SEPARATOR}; margin: 4px 8px; }}
    QMessageBox {{ background: {SURFACE}; color: {LABEL}; }}
    QMessageBox QLabel {{ color: {LABEL}; background: transparent; }}
    QMessageBox QPushButton {{
        color: {LABEL}; background: {FILL}; border: none;
        border-radius: 7px; padding: 5px 14px; min-width: 56px;
    }}
    QMessageBox QPushButton:hover {{ background: {FILL2}; }}

    /* 细滚动条：平时隐形，悬停显形 */
    QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px; }}
    QScrollBar::handle:vertical {{
        background: {FILL2}; border-radius: 3px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {SECONDARY}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QScrollBar:horizontal {{ background: transparent; height: 6px; margin: 2px; }}
    QScrollBar::handle:horizontal {{
        background: {FILL2}; border-radius: 3px; min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {SECONDARY}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    """

# ==================== 组件样式 ====================

def icon_btn() -> str:
    """标题栏图标按钮：无边框，悬停显灰底圆角"""
    return (
        "QPushButton { border: none; border-radius: 8px; font-size: 13px;"
        f" color: {SECONDARY}; background: transparent; padding: 0 2px; }}"
        f"QPushButton:hover {{ background: {FILL}; color: {LABEL}; }}"
    )

def nav_btn() -> str:
    """日期导航箭头"""
    return (
        "QPushButton { border: none; border-radius: 6px; font-size: 12px;"
        f" color: {TERTIARY}; background: transparent; }}"
        f"QPushButton:hover {{ background: {FILL}; color: {SECONDARY}; }}"
        f"QPushButton:disabled {{ color: rgba(128,128,128,0.4); }}"
    )

def close_btn() -> str:
    return (
        "QPushButton { border: none; border-radius: 8px; font-size: 16px;"
        f" color: {TERTIARY}; background: transparent; }}"
        f"QPushButton:hover {{ background: rgba(255,59,48,0.15); color: {RED}; }}"
    )

def format_btn() -> str:
    """格式工具栏按钮：无边框悬停显灰，视觉重量为零"""
    return (
        "QPushButton { border: none; border-radius: 7px; font-size: 12px;"
        f" color: {SECONDARY}; background: transparent; }}"
        f"QPushButton:hover {{ background: {FILL}; color: {LABEL}; }}"
    )

def format_btn_on() -> str:
    """格式按钮激活态（唯一使用强调色的地方之一）"""
    return (
        f"QPushButton {{ border: none; border-radius: 7px; font-size: 12px;"
        f" color: {BG}; background: {ACCENT}; font-weight: 600; }}"
    )

def date_chip() -> str:
    """日期胶囊：等宽数字"""
    return (
        "QLabel {"
        f" color: {SECONDARY}; font-size: 10px;"
        f" background: {FILL}; border-radius: 999px; padding: 1px 8px;"
        " font-variant-numeric: tabular-nums; }"
    )

def pill_palette(variant: str = "base") -> tuple[str, str, str]:
    """返回胶囊的背景、文字和边框颜色"""
    variants = {
        "base": (FILL, LABEL, "none"),
        "green": (GREEN_SOFT, GREEN_DEEP, "none"),
        "warn": (WARN_SOFT, WARN_DEEP, "none"),
        "blue": (BLUE_SOFT, BLUE, "none"),
        "ghost": ("transparent", SECONDARY, f"0.5px dashed {TERTIARY}"),
        "primary": (ACCENT, BG, "none"),
    }
    return variants.get(variant, variants["base"])

def pill(variant: str = "base") -> str:
    """胶囊样式：base / green / warn / ghost / blue"""
    bg, fg, border = pill_palette(variant)
    weight = "600;" if variant == "primary" else "500;"
    return (
        "QPushButton {"
        + (f" border: {border}; border-radius: 999px;" if border != "none"
           else " border: none; border-radius: 999px;")
        + f" padding: 2px 12px; font-size: 11px; font-weight: {weight}"
        + f" background: {bg}; color: {fg}; }}"
        f"QPushButton:hover {{ background: {ACCENT_HOVER if variant == 'primary' else (FILL2 if variant == 'base' else bg)}; }}"
    )

def dialog_qss() -> str:
    """对话框通用皮肤：卡片化 GroupBox / 圆角输入 / 主题按钮 / 滑块"""
    return f"""
    QLabel {{ background: transparent; }}
    QGroupBox {{
        background: {SURFACE}; border: 0.5px solid {SEPARATOR};
        border-radius: 12px; margin-top: 12px; padding: 14px 12px 10px;
        font-size: 13px; font-weight: 600; color: {LABEL};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 12px; top: 0px;
        color: {SECONDARY}; font-size: 11px; font-weight: 600;
    }}
    QLineEdit, QComboBox {{
        background: {INPUT_BG}; color: {LABEL};
        border: 0.5px solid {SEPARATOR}; border-radius: 8px;
        padding: 4px 8px; font-size: 12px;
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {SURFACE}; color: {LABEL};
        border: 0.5px solid {SEPARATOR}; border-radius: 8px;
        selection-background-color: {FILL}; selection-color: {LABEL};
    }}
    QPushButton[qss="secondary"] {{
        background: {FILL}; color: {LABEL}; border: none;
        border-radius: 8px; padding: 5px 16px; font-size: 12px; font-weight: 500;
    }}
    QPushButton[qss="secondary"]:hover {{ background: {FILL2}; }}
    QPushButton[qss="primary"] {{
        background: {ACCENT}; color: {BG}; border: none;
        border-radius: 8px; padding: 5px 16px; font-size: 12px; font-weight: 600;
    }}
    QPushButton[qss="primary"]:hover {{ background: {ACCENT_HOVER}; }}
    QCheckBox {{ spacing: 8px; color: {LABEL}; background: transparent; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 5px;
        border: 1.5px solid {TERTIARY}; background: transparent;
    }}
    QCheckBox::indicator:hover {{ border-color: {SECONDARY}; }}
    QCheckBox::indicator:checked {{
        background: {ACCENT}; border: 1.5px solid {ACCENT};
    }}
    QCheckBox::indicator:checked:hover {{
        background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER};
    }}
    QSlider::groove:horizontal {{
        height: 4px; border-radius: 2px; background: {FILL2};
    }}
    QSlider::handle:horizontal {{
        width: 18px; height: 18px; margin: -7px 0;
        border-radius: 9px; background: {SURFACE};
        border: 0.5px solid {SEPARATOR};
    }}
    QSlider::handle:horizontal:hover {{ border: 1.5px solid {ACCENT}; }}
    QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
    """

def calendar_qss() -> str:
    """QCalendarWidget 皮肤：去网格线、导航条融入卡片、 today 圆形强调"""
    return f"""
    QCalendarWidget {{
        background: {SURFACE}; color: {LABEL}; border: none;
    }}
    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background: transparent; border-bottom: 0.5px solid {SEPARATOR};
        min-height: 34px;
    }}
    QCalendarWidget QToolButton {{
        background: transparent; color: {LABEL};
        border: none; border-radius: 8px; padding: 4px 10px;
        font-size: 13px; font-weight: 600;
    }}
    QCalendarWidget QToolButton:hover {{ background: {FILL}; }}
    QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
    QCalendarWidget QSpinBox {{ background: {INPUT_BG}; color: {LABEL};
        border: 0.5px solid {SEPARATOR}; border-radius: 6px; }}
    QCalendarWidget QAbstractItemView:enabled {{
        color: {LABEL}; background: {SURFACE};
        selection-background-color: {ACCENT};
        selection-color: #FFFFFF; outline: none;
    }}
    QCalendarWidget QAbstractItemView:disabled {{ color: {TERTIARY}; }}
    QCalendarWidget QWidget#qt_calendar_calendarview {{
        outline: none; border: none; background: {SURFACE};
    }}
    """
