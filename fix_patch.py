import sys
sys.stdout.reconfigure(encoding="utf-8")

path = r"D:\project_code\Python_project\Engineer Desk\src\ui\main_window.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_toolbar = '''        # \u56de\u5230\u4eca\u5929\u6309\u94ae
        today_btn = QPushButton("\u56de\u5230\u4eca\u5929")
        today_btn.setFixedHeight(20)
        today_btn.setStyleSheet(
            "QPushButton { border: none; color: #888; font-size: 10px; }"
            "QPushButton:hover { color: #333; }"
        )
        today_btn.clicked.connect(self._goto_today)
        layout.addWidget(today_btn)'''

new_toolbar = '''        # \u5feb\u901f\u5207\u6362\uff1a\u524d\u4e00\u5929
        self._quick_prev_btn = QPushButton("\uff1c")
        self._quick_prev_btn.setFixedSize(20, 20)
        self._quick_prev_btn.setToolTip("\u524d\u4e00\u5929")
        self._quick_prev_btn.setStyleSheet(
            "QPushButton { border: none; color: #888; font-size: 10px; }"
            "QPushButton:hover { color: #333; }"
        )
        self._quick_prev_btn.clicked.connect(lambda: self._navigate_date("prev"))
        layout.addWidget(self._quick_prev_btn)

        # \u56de\u5230\u4eca\u5929\u6309\u94ae
        today_btn = QPushButton("\u56de\u5230\u4eca\u5929")
        today_btn.setFixedHeight(20)
        today_btn.setStyleSheet(
            "QPushButton { border: none; color: #888; font-size: 10px; }"
            "QPushButton:hover { color: #333; }"
        )
        today_btn.clicked.connect(self._goto_today)
        layout.addWidget(today_btn)

        # \u5feb\u901f\u5207\u6362\uff1a\u540e\u4e00\u5929
        self._quick_next_btn = QPushButton("\uff1e")
        self._quick_next_btn.setFixedSize(20, 20)
        self._quick_next_btn.setToolTip("\u540e\u4e00\u5929")
        self._quick_next_btn.setStyleSheet(
            "QPushButton { border: none; color: #888; font-size: 10px; }"
            "QPushButton:hover { color: #333; }"
        )
        self._quick_next_btn.clicked.connect(lambda: self._navigate_date("next"))
        layout.addWidget(self._quick_next_btn)'''

content = content.replace(old_toolbar, new_toolbar)

# \u66f4\u65b0 _update_nav_buttons \u540c\u6b65\u63a7\u5236\u8fd9\u4e24\u4e2a\u5feb\u901f\u6309\u94ae
old_nav = '''        self._prev_btn.setEnabled(prev is not None)
        self._next_btn.setEnabled(next_note is not None)'''

new_nav = '''        self._prev_btn.setEnabled(prev is not None)
        self._next_btn.setEnabled(next_note is not None)
        self._quick_prev_btn.setEnabled(prev is not None)
        self._quick_next_btn.setEnabled(next_note is not None)'''

content = content.replace(old_nav, new_nav)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("done")
