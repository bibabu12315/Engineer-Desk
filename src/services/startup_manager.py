"""
开机启动管理模块
管理 Windows 开机自启动的注册表项
"""

import os
import sys
import winreg


class StartupManager:
    """Windows 开机启动管理器"""

    # 注册表路径
    _REG_PATH: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _APP_NAME: str = "EngineerDesk"

    @classmethod
    def is_enabled(cls) -> bool:
        """检查是否已启用开机启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, cls._REG_PATH, 0, winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, cls._APP_NAME)
            winreg.CloseKey(key)
            return bool(value)
        except FileNotFoundError:
            return False

    @classmethod
    def enable(cls) -> None:
        """启用开机启动"""
        exe_path = sys.executable
        # 如果是通过 python 脚本运行，使用 pythonw 启动主脚本
        script_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
        )
        command = f'"{exe_path}" "{script_path}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, cls._REG_PATH, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, cls._APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

    @classmethod
    def disable(cls) -> None:
        """禁用开机启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls._REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.DeleteValue(key, cls._APP_NAME)
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
