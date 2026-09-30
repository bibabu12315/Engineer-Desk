"""
Engineer Desk - 桌面工程师工作台
主入口文件
"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.ui.main_window import StickyNoteWindow
from src.ui.system_tray import SystemTray


def main() -> None:
    """应用主入口"""
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("EngineerDesk")
    app.setOrganizationName("EngineerDesk")
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出程序

    # 创建主窗口
    window = StickyNoteWindow()

    # 创建系统托盘
    tray = SystemTray(
        show_callback=window.show_window,
        exit_callback=lambda: _quit_app(app, window),
        center_callback=lambda: window.center_on_primary_screen(),
    )

    # 连接关闭信号
    window.close_requested.connect(lambda: None)  # 隐藏到托盘

    # 显示窗口
    window.show_window()

    # 运行事件循环
    sys.exit(app.exec())


def _quit_app(app: QApplication, window: StickyNoteWindow) -> None:
    """安全退出应用"""
    window.close()  # 触发 closeEvent 保存数据
    app.quit()


if __name__ == "__main__":
    main()
