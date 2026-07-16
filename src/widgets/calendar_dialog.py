"""
日历对话框
显示月度日历，标注有记录的日期清晰显示，无记录日期灰显
"""

from datetime import date
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCalendarWidget,
    QPushButton, QLabel,
)
from PySide6.QtGui import QColor, QFont, QTextCharFormat

from src.database.db_manager import DatabaseManager


class CalendarDialog(QDialog):
    """日历对话框"""

    date_selected = Signal(str)  # 日期被选中 (YYYY-MM-DD)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db: DatabaseManager = DatabaseManager()
        self.setWindowTitle("日历")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(360, 380)

        self._init_ui()
        self._highlight_dates()

        # 监听月份切换以刷新高亮
        self._calendar.currentPageChanged.connect(self._highlight_dates)

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 标题
        title = QLabel("📅 日历")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        # 日历控件 —— 默认日期文字为浅灰色（无记录状态）
        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self._calendar.setStyleSheet(
            "QCalendarWidget QAbstractItemView:enabled { color: #d0d0d0; }"
        )
        self._calendar.clicked.connect(self._on_date_clicked)
        today = date.today()
        self._calendar.setSelectedDate(QDate(today.year, today.month, today.day))
        layout.addWidget(self._calendar)

        # 底部按钮
        btn_layout = QHBoxLayout()

        self._goto_today_btn = QPushButton("回到今天")
        self._goto_today_btn.clicked.connect(self._goto_today)
        btn_layout.addWidget(self._goto_today_btn)

        btn_layout.addStretch()

        self._date_label = QLabel("")
        self._date_label.setStyleSheet("color: #888;")
        btn_layout.addWidget(self._date_label)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _highlight_dates(self) -> None:
        """有记录的日期恢复正常颜色 + 黄色背景，无记录保持灰显"""
        dates = self._db.get_all_dates()

        # 有记录的高亮格式
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#FFE082"))
        highlight_format.setForeground(QColor("#333"))

        # 先清除所有旧的高亮
        empty_format = QTextCharFormat()
        self._calendar.setDateTextFormat(QDate(), empty_format)

        for d in dates:
            try:
                dt = date.fromisoformat(d)
                qdate = QDate(dt.year, dt.month, dt.day)
                self._calendar.setDateTextFormat(qdate, highlight_format)
            except ValueError:
                pass

    def _on_date_clicked(self, qdate: QDate) -> None:
        """日期被点击"""
        selected = qdate.toString("yyyy-MM-dd")
        self._date_label.setText(selected)
        self.date_selected.emit(selected)

    def _goto_today(self) -> None:
        """回到今天"""
        today = date.today()
        qdate = QDate(today.year, today.month, today.day)
        self._calendar.setSelectedDate(qdate)
        self._on_date_clicked(qdate)
