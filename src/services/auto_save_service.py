"""
自动保存服务
使用防抖机制，在用户停止输入指定时间后自动保存数据
"""

from PySide6.QtCore import QTimer, QObject


class AutoSaveService(QObject):
    """自动保存服务，基于 QTimer 实现防抖"""

    # 自动保存间隔：5 分钟（毫秒）
    _SAVE_INTERVAL_MS: int = 5 * 60 * 1000

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer: QTimer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._SAVE_INTERVAL_MS)
        self._timer.timeout.connect(self._on_timeout)
        self._save_callback: callable | None = None

    def set_callback(self, callback: callable) -> None:
        """设置保存回调函数"""
        self._save_callback = callback

    def trigger(self) -> None:
        """触发自动保存（重置计时器）"""
        self._timer.start()

    def save_now(self) -> None:
        """立即执行保存"""
        self._timer.stop()
        self._on_timeout()

    def _on_timeout(self) -> None:
        """计时器超时，执行保存"""
        if self._save_callback:
            self._save_callback()
