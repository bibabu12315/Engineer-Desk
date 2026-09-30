"""
路径管理模块
统一解析工程根目录、数据目录与数据库文件路径

设计目标：
1. 数据固定存放在工程内的 data/ 目录，便于备份与迁移；
2. 打包（PyInstaller）运行时同样指向工程内的 data/，避免 dist/ 被重新构建时数据被清空；
3. 支持通过环境变量 ENGINEERDESK_DATA_DIR 自定义数据目录位置。
"""

import os
import sys
from pathlib import Path


# 数据目录名称（位于工程根目录）
DATA_DIR_NAME: str = "data"
# 数据库文件名
DB_FILE_NAME: str = "engineer_desk.db"
# 允许通过环境变量覆盖数据目录
DATA_DIR_ENV: str = "ENGINEERDESK_DATA_DIR"


def is_frozen() -> bool:
    """判断当前是否运行在 PyInstaller 打包环境中"""
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> Path:
    """获取工程根目录

    打包运行时，从可执行文件所在目录逐级向上查找包含 src/ 与 main.py 的目录，
    从而定位到工程根，保证数据目录不会被 dist/ 重构清理。
    """
    if is_frozen():
        candidate = Path(sys.executable).resolve().parent
        for _ in range(4):
            if (candidate / "src").is_dir() and (candidate / "main.py").is_file():
                return candidate
            candidate = candidate.parent
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[2]


def get_data_dir() -> Path:
    """获取数据目录（不存在则自动创建）"""
    env_dir = os.environ.get(DATA_DIR_ENV, "").strip()
    if env_dir:
        path = Path(env_dir).expanduser().resolve()
    else:
        path = get_project_root() / DATA_DIR_NAME

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    """获取数据库文件完整路径"""
    return get_data_dir() / DB_FILE_NAME


def get_legacy_database_paths() -> list[Path]:
    """获取旧版本可能存放数据库的位置（用于历史数据迁移）"""
    candidates: list[Path] = []

    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        candidates.append(Path(appdata) / "EngineerDesk" / DB_FILE_NAME)

    candidates.append(get_project_root() / DB_FILE_NAME)

    return candidates
