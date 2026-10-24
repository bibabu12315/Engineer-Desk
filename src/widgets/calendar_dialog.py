"""
日历对话框（UI 重制版）
iOS 卡片质感：无网格线、导航条融入卡片、有记录日期橙色软底标注
"""

from datetime import date
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCalendarWidget,
    QPushButton, QLabel,
)
from PySide6.QtGui import QColor, QTextCharFormat

from src.database.db_manager import DatabaseManager
from src.ui import theme


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
        self.setMinimumSize(380, 400)
        self.setStyleSheet(theme.dialog_qss() + theme.calendar_qss())

        self._init_ui()
        self._highlight_dates()

        # 监听月份切换以刷新高亮
        self._calendar.currentPageChanged.connect(self._highlight_dates)

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        # 标题
        title = QLabel("日历")
        title.setStyleSheet(
            f"font-size: 17px; font-weight: 650; letter-spacing: -0.3px;"
            f" color: {theme.LABEL}; background: transparent;"
        )
        layout.addWidget(title)

        # 日历控件（去网格线，样式见 calendar_qss）
        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(False)
        self._calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self._calendar.clicked.connect(self._on_date_clicked)
        today = date.today()
        self._calendar.setSelectedDate(QDate(today.year, today.month, today.day))
        layout.addWidget(self._calendar, 1)

        # 底部：回今天（主操作）+ 选中日期 + 关闭
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._goto_today_btn = QPushButton("回到今天")
        self._goto_today_btn.setProperty("qss", "primary")
        self._goto_today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._goto_today_btn.clicked.connect(self._goto_today)
        btn_layout.addWidget(self._goto_today_btn)

        btn_layout.addStretch()

        self._date_label = QLabel("")
        self._date_label.setStyleSheet(
            f"color: {theme.SECONDARY}; font-size: 12px;"
            " font-variant-numeric: tabular-nums;"
        )
        btn_layout.addWidget(self._date_label)

        close_btn = QPushButton("关闭")
        close_btn.setProperty("qss", "secondary")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _highlight_dates(self) -> None:
        """有记录的日期：橙色软底 + 深橙文字（圆角由视图选择样式近似）"""
        dates = self._db.get_all_dates()

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(theme.ACCENT_SOFT))
        highlight_format.setForeground(QColor(theme.WARN_DEEP))
        # 加粗以增强辨识
        highlight_format.setFontWeight(650)

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
