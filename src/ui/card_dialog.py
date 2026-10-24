"""
无边框卡片对话框基类（UI 质感统一）
替代系统标题栏：圆角卡片 + 自定义标题行（标题 + × 关闭）+ 标题行可拖拽 + 投影
搜索 / 日历 / 设置三个弹窗统一继承此类
"""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor

from src.ui import theme

# 卡片外围留白（给投影留空间）
_MARGIN = 16


class CardDialog(QDialog):
    """无边框圆角卡片对话框"""

    def __init__(self, parent=None, title: str = "", size: tuple[int, int] = (420, 480)) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(theme.dialog_qss())
        self.resize(*size)

        # 卡片尺寸 = 窗口 - 投影留白
        card_w = size[0] - _MARGIN * 2

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)

        self._card = QWidget()
        self._card.setObjectName("card")
        self._card.setFixedWidth(card_w)
        self._card.setStyleSheet(
            f"QWidget#card {{ background: {theme.BG};"
            f" border-radius: 14px; }}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 55))
        self._card.setGraphicsEffect(shadow)
        outer.addWidget(self._card)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 10, 12, 14)
        card_layout.setSpacing(10)

        # ---- 自定义标题行 ----
        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet("background: transparent;")
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(
            f"font-size: 16px; font-weight: 650; letter-spacing: -0.3px;"
            f" color: {theme.LABEL}; background: transparent;"
        )
        h.addWidget(self._title_label)
        h.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("关闭")
        close_btn.setStyleSheet(theme.close_btn())
        close_btn.clicked.connect(self.close)
        h.addWidget(close_btn)

        card_layout.addWidget(header)

        # 子类往这里填内容
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        card_layout.addLayout(self.body, 1)

        self._drag_pos: QPoint | None = None
        self._header_height = 40  # 标题行 + 上边距，可拖拽区域

    def setTitle(self, text: str) -> None:
        self._title_label.setText(text)

    # ---- 标题行拖拽窗口 ----

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= _MARGIN + 30:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)
