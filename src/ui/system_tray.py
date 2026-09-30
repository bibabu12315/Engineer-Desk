"""
系统托盘模块
提供系统托盘图标和菜单（显示、退出、设置）
"""

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction

from src.services.config_manager import ConfigManager
from src.services.startup_manager import StartupManager


class SystemTray(QObject):
    """系统托盘管理"""

    def __init__(
        self,
        show_callback: callable,
        exit_callback: callable,
        center_callback: callable | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._show_callback: callable = show_callback
        self._exit_callback: callable = exit_callback
        self._center_callback: callable = center_callback
        self._config: ConfigManager = ConfigManager()

        self._tray: QSystemTrayIcon = QSystemTrayIcon(self)
        self._create_icon()
        self._create_menu()

        # 点击托盘图标显示窗口
        self._tray.activated.connect(self._on_activated)

        self._tray.show()

    def _create_icon(self) -> None:
        """创建托盘图标"""
        # 使用内置图标作为兜底
        icon = QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_ComputerIcon
        )
        self._tray.setIcon(icon)
        self._tray.setToolTip("Engineer Desk")

    def _create_menu(self) -> None:
        """创建右键菜单"""
        menu = QMenu()

        # 显示
        show_action = menu.addAction("显示")
        show_action.triggered.connect(self._show_callback)

        # 移动到主屏幕中央（外接屏拔掉后窗口可能不可见）
        if self._center_callback is not None:
            center_action = menu.addAction("移动到主屏幕中央")
            center_action.triggered.connect(lambda: self._center_callback())

        # 开机启动
        self._auto_start_action = menu.addAction("开机启动")
        self._auto_start_action.setCheckable(True)
        self._auto_start_action.setChecked(self._config.auto_start)
        self._auto_start_action.triggered.connect(self._toggle_auto_start)

        menu.addSeparator()

        # 退出
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self._exit_callback)

        self._tray.setContextMenu(menu)

        # 保存引用以便更新状态
        self._menu = menu

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盘图标被点击"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_callback()

    def _toggle_auto_start(self, enabled: bool) -> None:
        """切换开机启动"""
        if enabled:
            StartupManager.enable()
        else:
            StartupManager.disable()
        self._config.auto_start = enabled

    def update_auto_start_state(self) -> None:
        """更新开机启动菜单状态"""
        enabled = StartupManager.is_enabled()
        self._auto_start_action.setChecked(enabled)
        self._config.auto_start = enabled

    def show_message(self, title: str, message: str) -> None:
        """显示托盘消息"""
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
