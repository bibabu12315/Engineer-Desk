"""
便签文本编辑器控件
提供自由文本输入区域，支持字体、字号、背景色和透明度设置
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout
from PySide6.QtGui import QFont, QColor


class StickyEditor(QTextEdit):
    """便签文本编辑器"""

    content_changed = Signal()  # 内容变更信号

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("在这里记录今天的想法...")
        self.setFrameShape(QTextEdit.Shape.NoFrame)
        self.setStyleSheet("QTextEdit { background: transparent; }")

        # 默认字体
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 12
        self._apply_font()

        self.textChanged.connect(self.content_changed.emit)

    def _apply_font(self) -> None:
        """应用字体设置"""
        font = QFont(self._font_family, self._font_size)
        self.setFont(font)

    def set_font_family(self, family: str) -> None:
        """设置字体"""
        self._font_family = family
        self._apply_font()

    def set_font_size(self, size: int) -> None:
        """设置字号"""
        self._font_size = size
        self._apply_font()

    @property
    def font_family(self) -> str:
        return self._font_family

    @property
    def font_size(self) -> int:
        return self._font_size

    def set_plain_content(self, text: str) -> None:
        """设置纯文本内容（不触发变更信号）"""
        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)

    def get_plain_content(self) -> str:
        """获取纯文本内容"""
        return self.toPlainText()
