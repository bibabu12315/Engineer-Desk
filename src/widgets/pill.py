"""Rounded labels and buttons for capsule-shaped UI elements."""

from PySide6.QtCore import Qt, QEvent, QRectF, QSize
from PySide6.QtGui import (
    QColor, QEnterEvent, QFont, QFontMetrics, QPaintEvent, QPainter, QPen,
)
from PySide6.QtWidgets import QLabel, QPushButton

from src.ui import theme


def _color(value: str) -> QColor:
    if value.startswith("rgba(") and value.endswith(")"):
        red, green, blue, alpha = value[5:-1].split(",")
        return QColor(
            int(red), int(green), int(blue), round(float(alpha) * 255)
        )
    return QColor(value)


class PillButton(QPushButton):
    """A QPushButton that paints its background as a true capsule."""

    def __init__(self, text: str, variant: str = "base", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = self.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        self.set_variant(variant)

    def sizeHint(self) -> QSize:
        return QSize(QFontMetrics(self.font()).horizontalAdvance(self.text()) + 24,
                     max(18, QFontMetrics(self.font()).height() + 4))

    def set_variant(self, variant: str) -> None:
        background, foreground, border = theme.pill_palette(variant)
        self._background = _color(background)
        self._foreground = _color(foreground)
        self._hover_background = _color(
            theme.FILL2 if variant == "base" else background
        )
        self._border_color = (
            _color(theme.TERTIARY) if variant == "ghost" else None
        )
        self._dashed_border = border != "none" and variant == "ghost"
        self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setBrush(
            self._hover_background if self.underMouse() else self._background
        )
        if self._border_color is None:
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            pen = QPen(self._border_color, 0.5)
            if self._dashed_border:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        painter.setFont(self.font())
        painter.setPen(self._foreground)
        painter.drawText(
            rect.toRect().adjusted(12, 0, -12, 0),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )
        painter.end()
        event.accept()


class PillLabel(QLabel):
    """A label with a softly rounded date-chip background."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(8, 0, 8, 0)
        self.setFixedHeight(24)
        self.setStyleSheet(
            f"QLabel {{ color: {theme.SECONDARY}; background: transparent;"
            " border: none; font-size: 10px;"
            " font-variant-numeric: tabular-nums; }"
        )
        self._background = _color(theme.FILL)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._background)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        painter.end()
        super().paintEvent(event)
