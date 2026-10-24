"""
UI 设计令牌（Design Tokens）— iOS 质感主题（Light / Dark 双模式）
依据 docs/EngineerDesk-ui-redesign.html：
- 强调色只保留一种（iOS Orange），其余灰阶收敛为 Label/Secondary/Tertiary 三档
- 0.5px 发丝线替代边框；窗口 18 / 面板 12 / 按钮 8 / 胶囊 999 圆角
- 所有 QSS 都从这里取值，禁止散落硬编码色值

模式：main.py 启动时调用 init(app)，跟随系统深浅色；
colorSchemeChanged 时自动重应用（chrome 即时刷新，便签底色在下次加载便签时生效）。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette

MODE = "light"  # "light" | "dark"

# 便签底色：浅色默认暖纸白，深色默认暗纸黑（用户自定义色不覆盖）
PAPER_LIGHT = "#FFFDF8"
PAPER_DARK = "#1F1F21"
# 会被"跟随主题"的底色集合（旧默认 + 新默认）
# 会被"跟随主题"的底色集合（历代默认色；用户自定义色不在其中，原样保留）
THEME_DEFAULT_BGS = {PAPER_LIGHT, PAPER_DARK, "#FFFDE7", "#FDFBF7"}

# ==================== 双调色板 ====================

_LIGHT = dict(
    BG=PAPER_LIGHT, LABEL="#1C1C1E", SECONDARY="#8E8E93", TERTIARY="#C7C7CC",
    SEPARATOR="rgba(60,60,67,0.12)",
    FILL="rgba(120,120,128,0.08)", FILL2="rgba(120,120,128,0.16)",
    ACCENT="#FF9F0A", ACCENT_SOFT="#FFF4E0", ACCENT_HOVER="#E88F00",
    GREEN="#34C759", GREEN_SOFT="#E8F8EE", GREEN_DEEP="#1B7F3B",
    WARN_SOFT="#FFF0DC", WARN_DEEP="#B26A00",
    BLUE="#007AFF", BLUE_SOFT="#F0F6FF", RED="#FF3B30",
    INPUT_BG="#FFFFFF", SURFACE="#FFFFFF",
)

_DARK = dict(
    BG=PAPER_DARK, LABEL="#F2F2F7", SECONDARY="#98989E", TERTIARY="#5A5A5E",
    SEPARATOR="rgba(84,84,88,0.6)",
    FILL="rgba(120,120,128,0.24)", FILL2="rgba(120,120,128,0.32)",
    ACCENT="#FF9F0A", ACCENT_SOFT="rgba(255,159,10,0.18)", ACCENT_HOVER="#FFB340",
    GREEN="#30D158", GREEN_SOFT="rgba(48,209,88,0.18)", GREEN_DEEP="#30D158",
    WARN_SOFT="rgba(255,159,10,0.18)", WARN_DEEP="#FF9F0A",
    BLUE="#0A84FF", BLUE_SOFT="rgba(10,132,255,0.18)", RED="#FF453A",
    INPUT_BG="#2C2C2E", SURFACE="#2C2C2E",
)


def _apply(mode: str) -> None:
    """把对应调色板写入模块全局（所有 theme.X 取值都是运行时查全局）"""
    global MODE
    MODE = mode
    palette = _DARK if mode == "dark" else _LIGHT
    for k, v in palette.items():
        globals()[k] = v


_apply("light")

FONT_STACK = '"Microsoft YaHei", "PingFang SC", sans-serif'


def is_dark() -> bool:
    return MODE == "dark"


def init(app) -> None:
    """启动时按系统深浅色应用调色板，并监听切换"""
    hints = app.styleHints()
    scheme = None
    try:
        scheme = hints.colorScheme()
    except Exception:
        pass
    _apply("dark" if scheme == Qt.ColorScheme.Dark else "light")

    try:
        hints.colorSchemeChanged.connect(
            lambda scheme: (_apply(
                "dark" if scheme == Qt.ColorScheme.Dark else "light"
            ), app.setStyleSheet(app_qss()))
        )
    except Exception:
        pass  # 旧版 Qt 无 colorSchemeChanged，启动时定死


def note_paper(user_bg: str) -> str:
    """决定便签内容区底色：
    - 用户自定义过颜色（不在默认色集合里）→ 原样保留
    - 默认色 / 旧默认色 → 跟随主题（暗色用暗纸黑）
    """
    if user_bg and user_bg not in THEME_DEFAULT_BGS:
        return user_bg
    return PAPER_DARK if is_dark() else PAPER_LIGHT


# ==================== 全局 QSS ====================

def app_qss() -> str:
    """应用级 QSS：滚动条、菜单、ToolTip、输入光标等通用控件一次到位"""
    return f"""
    QWidget {{ font-family: {FONT_STACK}; color: {LABEL}; }}
    QTextEdit {{ color: {LABEL}; }}
    QLineEdit {{ color: {LABEL}; selection-background-color: {FILL2}; }}
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

def pill(variant: str = "base") -> str:
    """胶囊样式：base / green / warn / ghost / blue"""
    m = {
        "base":  (FILL, LABEL, "none"),
        "green": (GREEN_SOFT, GREEN_DEEP, "none"),
        "warn":  (WARN_SOFT, WARN_DEEP, "none"),
        "blue":  (BLUE_SOFT, BLUE, "none"),
        "ghost": ("transparent", SECONDARY, f"0.5px dashed {TERTIARY}"),
    }
    bg, fg, border = m.get(variant, m["base"])
    return (
        "QPushButton {"
        + (f" border: {border}; border-radius: 999px;" if border != "none"
           else " border: none; border-radius: 999px;")
        + f" padding: 1px 11px; font-size: 11px; font-weight: 500;"
        + f" background: {bg}; color: {fg}; }}"
        f"QPushButton:hover {{ background: {FILL2 if variant == 'base' else bg}; }}"
    )
