"""
数据库管理模块
负责 SQLite 数据库的初始化、连接管理和基础 CRUD 操作
"""

import sqlite3
import os
import re
from datetime import date, datetime
from typing import Optional


class DatabaseManager:
    """SQLite 数据库管理器，单例模式"""

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls, db_path: str = "") -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = "") -> None:
        if self._initialized:
            return
        self._initialized = True

        # 数据库文件存放在用户目录下，确保离线可用
        if not db_path:
            app_data = os.path.join(os.environ.get("APPDATA", ""), "EngineerDesk")
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, "engineer_desk.db")

        self._db_path: str = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_tables()
        self._migrate()

    def _connect(self) -> None:
        """建立数据库连接"""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def _init_tables(self) -> None:
        """初始化数据库表结构"""
        cursor = self._conn.cursor()

        # 便签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sticky_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                title TEXT DEFAULT '',
                content TEXT DEFAULT '',
                font_family TEXT DEFAULT 'Microsoft YaHei',
                font_size INTEGER DEFAULT 12,
                bg_color TEXT DEFAULT '#FDFBF7',
                opacity REAL DEFAULT 0.92,
                width INTEGER DEFAULT 400,
                height INTEGER DEFAULT 500,
                pos_x INTEGER DEFAULT 100,
                pos_y INTEGER DEFAULT 100,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # Todo 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sticky_note_id INTEGER NOT NULL,
                content TEXT DEFAULT '',
                completed INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                origin_date TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (sticky_note_id) REFERENCES sticky_notes(id) ON DELETE CASCADE
            )
        """)

        # Tag 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sticky_note_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY (sticky_note_id) REFERENCES sticky_notes(id) ON DELETE CASCADE,
                UNIQUE(sticky_note_id, tag_name)
            )
        """)

        # 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        self._conn.commit()

    def _migrate(self) -> None:
        """数据库迁移：为旧版本添加缺失的列"""
        cursor = self._conn.cursor()
        # 检查 origin_date 列是否存在
        cursor.execute("PRAGMA table_info(todos)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "origin_date" not in columns:
            try:
                cursor.execute("ALTER TABLE todos ADD COLUMN origin_date TEXT DEFAULT ''")
                self._conn.commit()
            except sqlite3.Error:
                pass

    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._connect()
        return self._conn

    # ==================== 便签操作 ====================

    def get_or_create_today_note(self) -> sqlite3.Row:
        """获取或创建今天的便签记录"""
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sticky_notes WHERE date = ?", (today,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO sticky_notes (date) VALUES (?)", (today,)
            )
            self.conn.commit()
            cursor.execute("SELECT * FROM sticky_notes WHERE date = ?", (today,))
            row = cursor.fetchone()
        return row

    def get_or_create_note_by_date(self, target_date: str) -> sqlite3.Row:
        """获取或创建指定日期的便签记录"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sticky_notes WHERE date = ?", (target_date,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO sticky_notes (date) VALUES (?)", (target_date,)
            )
            self.conn.commit()
            cursor.execute("SELECT * FROM sticky_notes WHERE date = ?", (target_date,))
            row = cursor.fetchone()
        return row

    def update_note(self, note_id: int, **kwargs) -> None:
        """更新便签字段（参数化查询，安全保留换行等特殊字符）"""
        allowed = {
            "title", "content", "font_family", "font_size",
            "bg_color", "opacity", "width", "height", "pos_x", "pos_y"
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return

        # 参数化查询：用 ? 占位符，避免 repr() 转义换行符等特殊字符
        set_parts = []
        params: list = []
        for k, v in updates.items():
            set_parts.append(f"{k} = ?")
            params.append(v)
        set_parts.append("updated_at = datetime('now','localtime')")
        set_clause = ", ".join(set_parts)
        params.append(note_id)

        try:
            self.conn.execute(
                f"UPDATE sticky_notes SET {set_clause} WHERE id = ?", params
            )
            self.conn.commit()
        except sqlite3.Error:
            self._reconnect()
            self.conn.execute(
                f"UPDATE sticky_notes SET {set_clause} WHERE id = ?", params
            )
            self.conn.commit()

    def _reconnect(self) -> None:
        """重新建立数据库连接"""
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        self._connect()

    def get_note_by_date(self, target_date: str) -> Optional[sqlite3.Row]:
        """根据日期获取便签"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sticky_notes WHERE date = ?", (target_date,))
        return cursor.fetchone()

    def get_note_by_id(self, note_id: int) -> Optional[sqlite3.Row]:
        """根据 ID 获取便签"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sticky_notes WHERE id = ?", (note_id,))
        return cursor.fetchone()

    def get_all_dates(self) -> list[str]:
        """获取所有有记录的日期列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT date FROM sticky_notes ORDER BY date DESC")
        return [row["date"] for row in cursor.fetchall()]

    def get_adjacent_note(self, current_date: str, direction: str) -> Optional[sqlite3.Row]:
        """获取相邻日期的便签"""
        cursor = self.conn.cursor()
        if direction == "prev":
            cursor.execute(
                "SELECT * FROM sticky_notes WHERE date < ? ORDER BY date DESC LIMIT 1",
                (current_date,),
            )
        else:
            cursor.execute(
                "SELECT * FROM sticky_notes WHERE date > ? ORDER BY date ASC LIMIT 1",
                (current_date,),
            )
        return cursor.fetchone()

    # ==================== Todo 操作 ====================

    def get_todos(self, note_id: int) -> list[sqlite3.Row]:
        """获取指定便签的所有 Todo"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM todos WHERE sticky_note_id = ? ORDER BY sort_order, id",
            (note_id,),
        )
        return cursor.fetchall()

    def add_todo(self, note_id: int, content: str = "", origin_date: str = "") -> sqlite3.Row:
        """新增 Todo"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM todos WHERE sticky_note_id = ?",
            (note_id,),
        )
        next_order = cursor.fetchone()[0]

        if not origin_date:
            # 新创建的 todo，origin_date 设为所属便签的日期
            row = self.get_note_by_id(note_id)
            origin_date = row["date"] if row else date.today().isoformat()

        cursor.execute(
            "INSERT INTO todos (sticky_note_id, content, sort_order, origin_date) VALUES (?, ?, ?, ?)",
            (note_id, content, next_order, origin_date),
        )
        self.conn.commit()
        cursor.execute("SELECT * FROM todos WHERE id = last_insert_rowid()")
        return cursor.fetchone()

    def update_todo(self, todo_id: int, **kwargs) -> None:
        """更新 Todo"""
        allowed = {"content", "completed", "sort_order"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self.conn.execute(
            f"UPDATE todos SET {set_clause} WHERE id = ?",
            (*updates.values(), todo_id),
        )
        self.conn.commit()

    def delete_todo(self, todo_id: int) -> None:
        """删除 Todo"""
        self.conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self.conn.commit()

    def get_uncompleted_todos(self, note_id: int) -> list[sqlite3.Row]:
        """获取未完成的 Todo"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM todos WHERE sticky_note_id = ? AND completed = 0 ORDER BY sort_order, id",
            (note_id,),
        )
        return cursor.fetchall()

    def carry_over_todos(self, from_note_id: int, to_note_id: int) -> int:
        """将未完成任务顺延到目标日期，返回顺延数量"""
        uncompleted = self.get_uncompleted_todos(from_note_id)
        count = 0
        for todo in uncompleted:
            self.add_todo(
                note_id=to_note_id,
                content=todo["content"],
                origin_date=todo["origin_date"] or self.get_note_by_id(from_note_id)["date"],
            )
            count += 1
        return count

    def get_today_completed_count(self, note_id: int) -> int:
        """获取今日已完成 Todo 数量"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM todos WHERE sticky_note_id = ? AND completed = 1",
            (note_id,),
        )
        return cursor.fetchone()[0]

    def calc_days_active(self, origin_date_str: str) -> int:
        """计算任务已持续天数"""
        if not origin_date_str:
            return 1
        try:
            origin = datetime.strptime(origin_date_str, "%Y-%m-%d").date()
            return (date.today() - origin).days + 1
        except ValueError:
            return 1

    # ==================== Tag 操作 ====================

    def get_tags(self, note_id: int) -> list[str]:
        """获取指定便签的所有标签"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT tag_name FROM note_tags WHERE sticky_note_id = ? ORDER BY tag_name",
            (note_id,),
        )
        return [row["tag_name"] for row in cursor.fetchall()]

    def set_tags(self, note_id: int, content: str) -> list[str]:
        """从内容中提取 #Tag 并更新数据库"""
        tags = self._extract_tags(content)
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM note_tags WHERE sticky_note_id = ?", (note_id,))
        for tag in tags:
            cursor.execute(
                "INSERT OR IGNORE INTO note_tags (sticky_note_id, tag_name) VALUES (?, ?)",
                (note_id, tag),
            )
        self.conn.commit()
        return tags

    def get_all_tags(self) -> list[str]:
        """获取所有使用过的标签"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT tag_name FROM note_tags ORDER BY tag_name")
        return [row["tag_name"] for row in cursor.fetchall()]

    @staticmethod
    def _extract_tags(text: str) -> list[str]:
        """从文本中提取 #Tag 标签"""
        pattern = r"#([\u4e00-\u9fff\w]+)"
        matches = re.findall(pattern, text)
        seen = set()
        result = []
        for tag in matches:
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
        return result

    # ==================== 搜索操作 ====================

    def search_notes(self, query: str) -> list[sqlite3.Row]:
        """搜索便签（标题、正文、标签）"""
        cursor = self.conn.cursor()
        like_pattern = f"%{query}%"
        cursor.execute("""
            SELECT DISTINCT sn.* FROM sticky_notes sn
            LEFT JOIN note_tags nt ON nt.sticky_note_id = sn.id
            WHERE sn.title LIKE ?
               OR sn.content LIKE ?
               OR nt.tag_name LIKE ?
            ORDER BY sn.date DESC
            LIMIT 50
        """, (like_pattern, like_pattern, like_pattern))
        return cursor.fetchall()

    def search_by_tag(self, tag_name: str) -> list[sqlite3.Row]:
        """根据标签搜索便签"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT sn.* FROM sticky_notes sn
            JOIN note_tags nt ON nt.sticky_note_id = sn.id
            WHERE nt.tag_name = ?
            ORDER BY sn.date DESC
        """, (tag_name,))
        return cursor.fetchall()

    # ==================== 配置操作 ====================

    def get_config(self, key: str, default: str = "") -> str:
        """获取配置值"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_config(self, key: str, value: str) -> None:
        """设置配置值"""
        self.conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
