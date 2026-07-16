"""
配置管理模块
管理应用级配置的读取和写入
"""

from src.database.db_manager import DatabaseManager


class ConfigManager:
    """应用配置管理器"""

    # 默认配置项
    DEFAULTS: dict[str, str] = {
        "auto_start": "0",
        "theme": "light",
    }

    def __init__(self) -> None:
        self._db: DatabaseManager = DatabaseManager()

    def get(self, key: str, default: str | None = None) -> str:
        """获取配置值，不存在时返回传入默认值或内置默认值"""
        value = self._db.get_config(key, "")
        if value == "":
            if default is not None:
                return default
            if key in self.DEFAULTS:
                return self.DEFAULTS[key]
        return value

    def set(self, key: str, value: str) -> None:
        """设置配置值"""
        self._db.set_config(key, value)

    @property
    def auto_start(self) -> bool:
        """是否开机启动"""
        return self.get("auto_start") == "1"

    @auto_start.setter
    def auto_start(self, value: bool) -> None:
        self.set("auto_start", "1" if value else "0")
