"""
便签文本编辑器控件
基于 QPlainTextEdit，原生支持纯文本换行，粘贴自动去格式
"""

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtWidgets import QPlainTextEdit, QWidget
from PySide6.QtGui import QFont


class StickyEditor(QPlainTextEdit):
    """便签文本编辑器（纯文本，无富文本干扰）"""

    content_changed = Signal()  # 内容变更信号

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("在这里记录今天的想法...")
        self.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.setStyleSheet("QPlainTextEdit { background: transparent; }")

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

    def insertFromMimeData(self, source: QMimeData) -> None:
        """重写粘贴行为：只接受纯文本，丢弃所有格式"""
        if source.hasText():
            self.insertPlainText(source.text())
