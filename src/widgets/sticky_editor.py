"""
便签文本编辑器控件（V2.0-a 富文本版）
基于 QTextEdit：支持加粗/斜体/删除线/下划线/高亮/待办行/分割线
存储策略：无格式时存纯文本（兼容旧数据），有格式时存 HTML
粘贴仍强制去格式（丢弃外来富文本）；剪贴板图片粘贴为内嵌图片（V2.2）
"""

import base64
import re

from PySide6.QtCore import QBuffer, QIODevice, Qt, QUrl, QMimeData, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor, QBrush, QTextBlockFormat, QTextImageFormat, QImage


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
            re.search(
                r"<(span|img|hr|b|i|u|s|strike|font|a)\b|style\s*=|href\s*=",
                text,
                re.IGNORECASE,
            )
        )

    def set_content(self, text: str) -> None:
        """设置内容（自动识别 HTML / 纯文本，不触发变更信号）"""
        self.blockSignals(True)
        if text and self._looks_like_html(text):
            self.setHtml(text)
        else:
            self.setPlainText(text or "")
        # 纯文本里的网址也识别成链接
        self._linkify_range(0, len(text or ""))
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
            r"|background-color|color\s*:\s*#(?!(000000|000\b))|<hr\b|<img\b|href\s*=",
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
        cursor.insertText("─" * 12)
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

    # 便签内图片最大显示宽度（px），超出按比例缩小
    _MAX_IMG_W = 480
    # 单张图片 base64 后的最大体积（约 2MB），超出拒绝插入并保护存储
    _MAX_IMG_BYTES = 2 * 1024 * 1024
    # 支持粘贴的图片文件扩展名
    _IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

    def insertFromMimeData(self, source: QMimeData) -> None:
        """重写粘贴行为：图片直接内嵌；文本仍只接受纯文本"""
        if source.hasImage():
            img = QImage(source.imageData())
            if not img.isNull():
                self._insert_image(img)
            return
        # 资源管理器里复制的图片文件（URL 带本地路径）
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(
                    tuple(self._IMG_EXTS)
                ):
                    img = QImage(url.toLocalFile())
                    if not img.isNull():
                        self._insert_image(img)
                    return
        if source.hasText():
            text = source.text()
            pos = self.textCursor().position()
            self.insertPlainText(text)
            # 粘贴内容里的 http(s) 文本自动转成链接
            self._linkify_range(pos, pos + len(text))
            return

    def _insert_image(self, img: QImage) -> None:
        """把图片转 PNG base64 内嵌到光标处（随笔记 HTML 存储，无需外部文件）"""
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        data = buf.data()
        if data.size() > self._MAX_IMG_BYTES:
            return
        b64 = base64.b64encode(bytes(data)).decode("ascii")
        fmt = QTextImageFormat()
        fmt.setName(f"data:image/png;base64,{b64}")
        # 超宽图片按比例缩小到便签宽度内
        if img.width() > self._MAX_IMG_W:
            fmt.setWidth(self._MAX_IMG_W)
            fmt.setHeight(round(img.height() * self._MAX_IMG_W / img.width()))
        self.textCursor().insertImage(fmt)
        # 图片后补一个空块，避免连续图片粘在同一行挤在一起
        cursor = self.textCursor()
        if cursor.block().text():
            cursor.insertBlock()

    # ==================== 超链接（V2.2-b） ====================

    _URL_RE = re.compile(r"https?://[^\s<>()\[\]{}'\"，。）】]+")

    def _link_format(self, url: str) -> QTextCharFormat:
        """链接样式：主题链接色 + 下划线（不用硬编码蓝，跟随明暗主题）"""
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(url)
        fmt.setForeground(self.palette().link())
        fmt.setFontUnderline(True)
        return fmt

    def _linkify_range(self, start: int, end: int) -> None:
        """把 [start, end) 范围内出现的 http(s) 文本转成可点击链接
        
        已经是链接的部分跳过，避免重复套锚点。
        """
        doc = self.document()
        block = doc.findBlock(start)
        while block.isValid() and block.position() < end:
            text = block.text()
            for m in self._URL_RE.finditer(text):
                # 已在该链接内则跳过（避免重复处理）
                cur = QTextCursor(doc)
                cur.setPosition(block.position() + m.start())
                if cur.charFormat().anchorHref():
                    continue
                cur.setPosition(block.position() + m.end(), QTextCursor.MoveMode.KeepAnchor)
                cur.mergeCharFormat(self._link_format(m.group(0)))
            block = block.next()

    def _anchor_range_at(self, pos) -> QTextCursor | None:
        """返回光标处所在链接的完整选区；不在链接上返回 None"""
        url = self.anchorAt(pos)
        if not url:
            return None
        cursor = self.cursorForPosition(pos)
        block = cursor.block()
        text = block.text()
        i = cursor.position() - block.position()
        # 向左右扩展到链接边界
        left = i
        while left > 0:
            c = QTextCursor(self.document())
            c.setPosition(block.position() + left - 1)
            if c.charFormat().anchorHref() != url:
                break
            left -= 1
        right = i
        while right < len(text):
            c = QTextCursor(self.document())
            c.setPosition(block.position() + right)
            if c.charFormat().anchorHref() != url:
                break
            right += 1
        sel = QTextCursor(self.document())
        sel.setPosition(block.position() + left)
        sel.setPosition(block.position() + right, QTextCursor.MoveMode.KeepAnchor)
        return sel

    def remove_link_at(self, pos) -> None:
        """取消光标处的链接（保留文字，恢复普通样式）"""
        sel = self._anchor_range_at(pos)
        if sel is None:
            return
        fmt = QTextCharFormat()
        fmt.setAnchor(False)
        fmt.setAnchorHref("")
        fmt.setFontUnderline(False)
        fmt.setForeground(self.palette().text())
        sel.beginEditBlock()
        sel.mergeCharFormat(fmt)
        sel.endEditBlock()

    def mouseMoveEvent(self, event) -> None:
        """悬停在链接上：手型光标 + 显示完整 URL"""
        url = self.anchorAt(event.position().toPoint())
        self.viewport().setCursor(
            Qt.CursorShape.PointingHandCursor if url else Qt.CursorShape.IBeamCursor
        )
        self.setToolTip(url if url else "")
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Ctrl + 单击打开链接（纯单击留给正常编辑光标定位）"""
        url = self.anchorAt(event.position().toPoint())
        if url and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            QDesktopServices.openUrl(QUrl(url))
            event.accept()
            return
        super().mousePressEvent(event)

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
        # 光标在链接上：打开 / 复制地址 / 取消链接
        url = self.anchorAt(event.pos())
        if url:
            menu.addSeparator()
            menu.addAction("打开链接", lambda: QDesktopServices.openUrl(QUrl(url)))
            menu.addAction(
                "复制链接地址", lambda: QGuiApplication.clipboard().setText(url)
            )
            menu.addAction("取消链接", lambda: self.remove_link_at(event.pos()))
        if block_text is not None:
            menu.addSeparator()
            act = menu.addAction("归档到项目 ▾")
            act.triggered.connect(
                lambda checked=False, t=block_text: self.archive_requested.emit(t)
            )
        menu.exec(event.globalPos())
