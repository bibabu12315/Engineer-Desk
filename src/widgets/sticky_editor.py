"""
便签文本编辑器控件（V2.0-a 富文本版）
基于 QTextEdit：支持加粗/斜体/删除线/下划线/高亮/待办行/分割线
存储策略：无格式时存纯文本（兼容旧数据），有格式时存 HTML
粘贴仍强制去格式（丢弃外来富文本）
"""

import re

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor, QBrush, QTextBlockFormat


class StickyEditor(QTextEdit):
    """便签编辑器：轻量富文本（按钮驱动，无 Markdown 语法）"""

    content_changed = Signal()  # 内容变更信号
    archive_requested = Signal(str)  # 右键分割线块请求归档（携带块纯文本）

    # 高亮标准色（荧光笔风格，小巧够用）
    HIGHLIGHT_COLORS: list[tuple[str, str]] = [
        ("黄", "#FFF176"),
        ("绿", "#A5D6A7"),
        ("蓝", "#90CAF9"),
        ("粉", "#F48FB1"),
        ("橙", "#FFB74D"),
        ("紫", "#CE93D8"),
    ]
    # 待办行前缀字符
    _TODO_OPEN = "☐ "
    _TODO_DONE = "☑ "

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("在这里记录今天的想法...")
        self.setFrameShape(QTextEdit.Shape.NoFrame)
        self.setStyleSheet("QTextEdit { background: transparent; }")
        self.setAcceptRichText(True)

        # 默认字体
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 12
        self._apply_font()

        self.textChanged.connect(self.content_changed.emit)

    # ==================== 字体 ====================

    def _apply_font(self) -> None:
        """应用字体设置（作为文档默认字体）"""
        font = QFont(self._font_family, self._font_size)
        self.document().setDefaultFont(font)
        self.setFont(font)

    def set_font_family(self, family: str) -> None:
        self._font_family = family
        self._apply_font()

    def set_font_size(self, size: int) -> None:
        self._font_size = size
        self._apply_font()

    @property
    def font_family(self) -> str:
        return self._font_family

    @property
    def font_size(self) -> int:
        return self._font_size

    # ==================== 内容读写（HTML / 纯文本自适应） ====================

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        """判断存储内容是否含富文本标记"""
        return bool(
            re.search(r"<(span|hr|b|i|u|s|strike|font)\b|style\s*=", text, re.IGNORECASE)
        )

    def set_content(self, text: str) -> None:
        """设置内容（自动识别 HTML / 纯文本，不触发变更信号）"""
        self.blockSignals(True)
        if text and self._looks_like_html(text):
            self.setHtml(text)
        else:
            self.setPlainText(text or "")
        # 清掉残留的"当前字符格式"，避免光标处继续输入时继承旧高亮/加粗
        self.setCurrentCharFormat(QTextCharFormat())
        cursor = self.textCursor()
        cursor.setBlockFormat(QTextBlockFormat())
        self.setTextCursor(cursor)
        self.blockSignals(False)

    def get_content(self) -> str:
        """获取存储内容：有格式存 HTML，无格式存纯文本"""
        html = self.toHtml()
        if re.search(
            r"font-weight\s*:\s*(bold|[6-9]00)|font-style\s*:\s*italic"
            r"|text-decoration[^;]*underline|text-decoration[^;]*line-through"
            r"|background-color|color\s*:\s*#(?!(000000|000\b))|<hr\b",
            html,
            re.IGNORECASE,
        ):
            return html
        return self.toPlainText()

    # 兼容旧接口
    def set_plain_content(self, text: str) -> None:
        self.set_content(text)

    def get_plain_content(self) -> str:
        return self.toPlainText()

    # ==================== 格式操作 ====================

    def _merge_fmt(self, fmt: QTextCharFormat) -> None:
        self.textCursor().mergeCharFormat(fmt)

    def toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        cur = self.textCursor().charFormat()
        bold = cur.fontWeight() >= QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if bold else QFont.Weight.Bold)
        self._merge_fmt(fmt)

    def toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.textCursor().charFormat().fontItalic())
        self._merge_fmt(fmt)

    def toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.textCursor().charFormat().fontUnderline())
        self._merge_fmt(fmt)

    def toggle_strike(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not self.textCursor().charFormat().fontStrikeOut())
        self._merge_fmt(fmt)

    def set_highlight(self, color: QColor | None) -> None:
        """给选区设置高亮色；color 为 None 表示清除高亮"""
        fmt = QTextCharFormat()
        if color is None:
            fmt.setBackground(QBrush(Qt.BrushStyle.NoBrush))
        else:
            fmt.setBackground(color)
        self._merge_fmt(fmt)

    def toggle_todo_line(self) -> None:
        """当前行切换为待办行：☐ 未完成 / ☑ 完成 / 普通行 三态循环"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
        )
        text = cursor.selectedText()
        if text.startswith(self._TODO_OPEN):
            new_text = self._TODO_DONE + text[len(self._TODO_OPEN):]
        elif text.startswith(self._TODO_DONE):
            new_text = text[len(self._TODO_DONE):]
        else:
            new_text = self._TODO_OPEN + text
        cursor.insertText(new_text)
        cursor.endEditBlock()

    def insert_divider(self) -> None:
        """光标处插入分割线（品牌橙细划线，另起一段，居中）

        不用 <hr>：QTextEdit 导出 HTML 时 hr 之后的内容会丢失。
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.block().text().strip():
            cursor.insertBlock()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#FF9F0A"))
        cursor.setCharFormat(fmt)
        cursor.insertText("─" * 24)
        # 分割线所在块居中（视觉上更像分隔符而非正文）
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        bf = QTextBlockFormat()
        bf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cursor.setBlockFormat(bf)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertBlock()
        bf = QTextBlockFormat()
        bf.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cursor.setBlockFormat(bf)
        cursor.setCharFormat(QTextCharFormat())
        cursor.endEditBlock()

    # ==================== 粘贴行为 ====================

    def insertFromMimeData(self, source: QMimeData) -> None:
        """重写粘贴行为：只接受纯文本，丢弃所有格式"""
        if source.hasText():
            self.insertPlainText(source.text())

    # ==================== 分割线块与归档（V2.0-d） ====================

    @staticmethod
    def _is_divider(text: str) -> bool:
        """判断一行是否为分割线（连续 ─ 字符）"""
        stripped = text.strip()
        return len(stripped) >= 4 and set(stripped) == {"─"}

    def _current_divider_block_text(self) -> str | None:
        """返回光标所在分割线块（相邻两条分割线之间的内容）的纯文本

        - 光标不在任何块内 / 无分割线 / 光标正压在分割线上：返回 None
        - 块内保留待办前缀等原始文本
        """
        doc = self.document()
        current_block = self.textCursor().block()
        blocks = []
        b = doc.firstBlock()
        while b.isValid():
            blocks.append(b)
            b = b.next()

        # 定位当前块的索引
        try:
            idx = next(i for i, blk in enumerate(blocks) if blk.position() == current_block.position())
        except StopIteration:
            return None

        if self._is_divider(blocks[idx].text()):
            return None

        # 向上找最近的分割线，向下找最近的分割线
        start = 0
        for i in range(idx - 1, -1, -1):
            if self._is_divider(blocks[i].text()):
                start = i + 1
                break
        else:
            start = 0
        end = len(blocks)
        for i in range(idx + 1, len(blocks)):
            if self._is_divider(blocks[i].text()):
                end = i
                break

        lines = [blocks[i].text() for i in range(start, end)]
        text = "\n".join(lines).strip()
        return text if text else None

    def contextMenuEvent(self, event) -> None:
        """右键菜单：标准菜单 +（位于分割线块内时）归档到项目"""
        menu = self.createStandardContextMenu()
        block_text = self._current_divider_block_text()
        if block_text is not None:
            menu.addSeparator()
            act = menu.addAction("归档到项目 ▾")
            act.triggered.connect(
                lambda checked=False, t=block_text: self.archive_requested.emit(t)
            )
        menu.exec(event.globalPos())
