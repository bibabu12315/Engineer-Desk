"""
标签栏控件
显示和管理便签的 #Tag 标签
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtGui import QFont


class TagBar(QWidget):
    """标签栏，显示当前便签的标签"""

    tag_clicked = Signal(str)  # 标签被点击信号

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tags: list[str] = []

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 2, 8, 2)
        self._layout.setSpacing(4)

        self._label = QLabel("🏷")
        self._label.setStyleSheet("font-size: 12px;")
        self._layout.addWidget(self._label)

        self._layout.addStretch()

    def set_tags(self, tags: list[str]) -> None:
        """设置标签列表"""
        self._tags = tags
        self._rebuild()

    def _rebuild(self) -> None:
        """重建标签按钮"""
        # 清除旧标签按钮（保留前面的 label）
        while self._layout.count() > 2:
            item = self._layout.takeAt(2)
            if item.widget():
                item.widget().deleteLater()

        for tag in self._tags:
            btn = QPushButton(f"#{tag}")
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { border: none; border-radius: 999px;"
                " padding: 0 10px; font-size: 11px; font-weight: 500;"
                " background: rgba(120,120,128,0.08); color: #5F5E5A; }"
                "QPushButton:hover { background: rgba(120,120,128,0.16); color: #1C1C1E; }"
            )
            # 用默认参数捕获当前 tag 值
            btn.clicked.connect(
                lambda checked, t=tag: self.tag_clicked.emit(t)
            )
            self._layout.addWidget(btn)

        self._layout.addStretch()
