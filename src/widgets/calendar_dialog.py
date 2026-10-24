"""
日历对话框（对齐细化设计稿 §7）
卡片质感：无网格线、周一起始、周末不标红、有记录日期橙色软底、今天实底橙
"""

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QPushButton, QLabel,
)

from src.database.db_manager import DatabaseManager
from src.ui import theme
from src.ui.card_dialog import CardDialog


class CalendarDialog(CardDialog):
    """日历对话框"""

    date_selected = Signal(str)  # 日期被选中 (YYYY-MM-DD)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, title="日历", size=(412, 432))
        self._db: DatabaseManager = DatabaseManager()
        today = QDate.currentDate()
        self._displayed_month = QDate(today.year(), today.month(), 1)
        self._selected_date = today

        self._init_body()

        header = self._card.layout().itemAt(0).widget()
        header.hide()
        self._card.layout().setContentsMargins(16, 12, 16, 14)
        self._card.layout().setSpacing(0)
        self._render_month()

    def _init_body(self) -> None:
        calendar_card = QFrame()
        calendar_card.setObjectName("calendarCard")
        calendar_card.setStyleSheet(
            f"QFrame#calendarCard {{ background: {theme.SURFACE};"
            f" border: 1px solid {theme.SEPARATOR}; border-radius: 16px; }}"
        )
        calendar_layout = QVBoxLayout(calendar_card)
        calendar_layout.setContentsMargins(12, 8, 12, 10)
        calendar_layout.setSpacing(6)

        month_header = QHBoxLayout()
        month_header.setContentsMargins(0, 0, 0, 0)
        month_header.setSpacing(4)

        previous_button = QPushButton("◀")
        previous_button.setObjectName("previousMonthButton")
        previous_button.setFixedSize(28, 30)
        previous_button.setCursor(Qt.CursorShape.PointingHandCursor)
        previous_button.setStyleSheet(self._month_button_style())
        previous_button.clicked.connect(lambda: self._change_month(-1))
        month_header.addWidget(previous_button)

        self._month_label = QLabel()
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._month_label.setStyleSheet(
            f"color: {theme.LABEL}; font-size: 16px; font-weight: 700;"
            " background: transparent;"
        )
        month_header.addWidget(self._month_label, 1)

        next_button = QPushButton("▶")
        next_button.setObjectName("nextMonthButton")
        next_button.setFixedSize(28, 30)
        next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        next_button.setStyleSheet(self._month_button_style())
        next_button.clicked.connect(lambda: self._change_month(1))
        month_header.addWidget(next_button)

        close_button = QPushButton("×")
        close_button.setObjectName("closeCalendarButton")
        close_button.setToolTip("关闭日历")
        close_button.setFixedSize(26, 26)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setStyleSheet(theme.close_btn())
        close_button.clicked.connect(self.close)
        month_header.addWidget(close_button)
        calendar_layout.addLayout(month_header)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(
            f"background: {theme.SEPARATOR}; border: none;"
        )
        calendar_layout.addWidget(separator)

        self._days_grid = QGridLayout()
        self._days_grid.setContentsMargins(0, 0, 0, 0)
        self._days_grid.setHorizontalSpacing(2)
        self._days_grid.setVerticalSpacing(2)

        for column, label in enumerate(("日", "一", "二", "三", "四", "五", "六")):
            weekday = QLabel(label)
            weekday.setAlignment(Qt.AlignmentFlag.AlignCenter)
            weekday.setFixedHeight(24)
            weekday.setStyleSheet(
                f"color: {theme.SECONDARY}; font-size: 12px;"
                " background: transparent;"
            )
            self._days_grid.addWidget(weekday, 0, column)
            self._days_grid.setColumnStretch(column, 1)
        calendar_layout.addLayout(self._days_grid)
        self.body.addWidget(calendar_card, 1)

        # 底部：图例 + 回到今天（主操作）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        legend = QLabel("🟧 有记录 · ■ 今天")
        legend.setStyleSheet(
            f"color: {theme.SECONDARY}; font-size: 12px;"
        )
        btn_layout.addWidget(legend)
        btn_layout.addStretch()

        self._goto_today_btn = QPushButton("回到今天")
        self._goto_today_btn.setProperty("qss", "primary")
        self._goto_today_btn.setFixedSize(120, 44)
        self._goto_today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._goto_today_btn.clicked.connect(self._goto_today)
        btn_layout.addWidget(self._goto_today_btn)

        self.body.addLayout(btn_layout)

    @staticmethod
    def _month_button_style() -> str:
        return (
            "QPushButton { border: none; border-radius: 8px;"
            f" color: {theme.LABEL}; background: transparent;"
            " font-size: 14px; font-weight: 700; }"
            f"QPushButton:hover {{ background: {theme.FILL}; }}"
        )

    @staticmethod
    def _day_button_style(background: str, foreground: str, weight: int = 400) -> str:
        return (
            "QPushButton { border: none; border-radius: 9px;"
            f" color: {foreground}; background: {background};"
            f" font-size: 13px; font-weight: {weight}; }}"
            f"QPushButton:hover {{ background: {theme.ACCENT_SOFT};"
            f" color: {theme.WARN_DEEP}; }}"
        )

    def _change_month(self, offset: int) -> None:
        self._displayed_month = self._displayed_month.addMonths(offset)
        self._render_month()

    def _highlight_dates(self) -> None:
        """Refresh the month grid when note dates change."""
        self._render_month()

    def _render_month(self) -> None:
        """Render a Sunday-first month grid with recorded dates highlighted."""
        while self._days_grid.count() > 7:
            item = self._days_grid.takeAt(7)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        year = self._displayed_month.year()
        month = self._displayed_month.month()
        self._month_label.setText(f"{year}年 {month}月")

        first_day = QDate(year, month, 1)
        offset = first_day.dayOfWeek() % 7
        day_count = first_day.daysInMonth()
        cell_count = ((offset + day_count + 6) // 7) * 7
        today = QDate.currentDate()
        recorded_dates = set(self._db.get_all_dates())

        for index in range(cell_count):
            current_date = first_day.addDays(index - offset)
            in_month = current_date.month() == month
            date_string = current_date.toString("yyyy-MM-dd")
            is_selected = current_date == self._selected_date
            is_recorded = in_month and date_string in recorded_dates

            if is_selected:
                background, foreground, weight = theme.ACCENT, "#FFFFFF", 700
            elif is_recorded:
                background, foreground, weight = theme.ACCENT_SOFT, theme.WARN_DEEP, 500
            elif not in_month:
                background, foreground, weight = "transparent", theme.TERTIARY, 400
            else:
                background, foreground, weight = "transparent", theme.LABEL, 400

            button = QPushButton(str(current_date.day()))
            button.setObjectName(f"calendarDate_{date_string}")
            button.setProperty("date", date_string)
            button.setProperty("hasRecord", is_recorded)
            button.setProperty("isToday", current_date == today)
            button.setFixedHeight(36)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                self._day_button_style(background, foreground, weight)
                + (
                    f"QPushButton:hover {{ background: {theme.ACCENT_HOVER};"
                    " color: #FFFFFF; }"
                    if is_selected else ""
                )
            )
            button.clicked.connect(
                lambda _checked=False, value=current_date: self._on_date_clicked(value)
            )
            self._days_grid.addWidget(
                button,
                1 + index // 7,
                index % 7,
            )

    def _on_date_clicked(self, qdate: QDate) -> None:
        self._selected_date = qdate
        if qdate.month() != self._displayed_month.month() or qdate.year() != self._displayed_month.year():
            self._displayed_month = QDate(qdate.year(), qdate.month(), 1)
        self._render_month()
        self.date_selected.emit(qdate.toString("yyyy-MM-dd"))

    def _goto_today(self) -> None:
        today = QDate.currentDate()
        self._selected_date = today
        self._displayed_month = QDate(today.year(), today.month(), 1)
        self._render_month()
        self.date_selected.emit(today.toString("yyyy-MM-dd"))
