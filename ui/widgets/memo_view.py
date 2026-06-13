from __future__ import annotations

import re
from datetime import datetime, timezone

from PyQt6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, QSignalBlocker, QTimer
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QTextBlockFormat,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextOption,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import storage.memo_store as memo_store
from storage.memo_store import Memo
from ui.assets import tinted_icon


LIST_MARGIN_X = 14
ITEM_GAP = 8


def preview_line(markdown: str) -> str:
    text = markdown.strip()
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"^(?:[-*+]\s+)?\[[ xX]\]\s+", "", text)
    text = re.sub(r"^[-*+]\s+", "", text)
    text = re.sub(r"^\d+\.\s+", "", text)
    text = re.sub(r'^"\s+', "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!~)~([^~]+)~(?!~)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)

        self._headings = []
        for size in (23, 19, 16, 14, 13, 13):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#11131a"))
            fmt.setFontPointSize(size)
            fmt.setFontWeight(QFont.Weight.Bold)
            self._headings.append(fmt)

        self._marker = QTextCharFormat()
        self._marker.setForeground(QColor("#2f80ff"))
        self._marker.setFontWeight(QFont.Weight.DemiBold)

        self._hidden_marker = QTextCharFormat()
        self._hidden_marker.setForeground(QColor(0, 0, 0, 0))
        self._hidden_marker.setFontPointSize(1)

        self._code = QTextCharFormat()
        self._code.setForeground(QColor("#344054"))
        self._code.setFontFamily("Menlo")
        self._code.setFontPointSize(12)

        self._inline_code = QTextCharFormat(self._code)
        self._inline_code.setBackground(QColor("#e8eef7"))
        self._inline_code.setForeground(QColor("#2d405a"))

        self._bold = QTextCharFormat()
        self._bold.setFontWeight(QFont.Weight.Bold)

        self._italic = QTextCharFormat()
        self._italic.setFontItalic(True)

        self._strike = QTextCharFormat()
        self._strike.setFontStrikeOut(True)

        self._link = QTextCharFormat()
        self._link.setForeground(QColor("#2f80ff"))
        self._link.setFontUnderline(True)

        self._quote = QTextCharFormat()
        self._quote.setForeground(QColor("#667085"))
        self._quote.setFontItalic(True)

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        in_code = self.previousBlockState() == 1
        stripped = text.lstrip()
        indent = len(text) - len(stripped)

        if stripped.startswith("```"):
            self.setFormat(indent, len(stripped), self._hidden_marker)
            self.setCurrentBlockState(0 if in_code else 1)
            return

        if in_code:
            self.setFormat(0, len(text), self._code)
            self.setCurrentBlockState(1)
            return

        self.setCurrentBlockState(0)

        heading_match = re.match(r"^(#{1,6})(\s*)(.*)$", stripped)
        if heading_match:
            marker_len = len(heading_match.group(1)) + len(heading_match.group(2))
            level = min(6, len(heading_match.group(1)))
            self.setFormat(indent, marker_len, self._hidden_marker)
            self.setFormat(indent + marker_len, len(text) - indent - marker_len, self._headings[level - 1])
        elif checkbox_match := re.match(r"^(?:-\s+)?\[[ xX]\]\s+", stripped):
            self.setFormat(indent, len(checkbox_match.group(0)), self._hidden_marker)
        elif re.match(r"^\d+\.\s+", stripped):
            marker_len = stripped.index(" ") + 1
            self.setFormat(indent, marker_len, self._marker)
        elif stripped.startswith(("- ", "* ", "+ ", '" ')):
            marker_format = self._hidden_marker if stripped.startswith('" ') else self._marker
            self.setFormat(indent, 2, marker_format)
            if stripped.startswith('" '):
                self.setFormat(indent + 2, len(text) - indent - 2, self._quote)

        self._highlight_wrapped(text, r"`([^`]+)`", self._inline_code)
        self._highlight_wrapped(text, r"\*\*([^*]+)\*\*", self._bold)
        self._highlight_wrapped(text, r"(?<!\*)\*([^*]+)\*(?!\*)", self._italic)
        self._highlight_wrapped(text, r"(?<!~)~([^~]+)~(?!~)", self._strike)
        self._highlight_inline(text, r"\[[^\]]+\]\([^)]+\)", self._link, include_markers=False)

    def _highlight_wrapped(self, text: str, pattern: str, fmt: QTextCharFormat) -> None:
        for match in re.finditer(pattern, text):
            marker_left = match.start(1) - match.start()
            marker_right = match.end() - match.end(1)
            self.setFormat(match.start(), marker_left, self._hidden_marker)
            self.setFormat(match.start(1), match.end(1) - match.start(1), fmt)
            self.setFormat(match.end(1), marker_right, self._hidden_marker)

    def _highlight_inline(self, text: str, pattern: str, fmt: QTextCharFormat, include_markers: bool) -> None:
        for match in re.finditer(pattern, text):
            start = match.start() if include_markers else match.start()
            length = match.end() - start
            self.setFormat(start, length, fmt)


class MemoTextEdit(QTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self._formatting_blocks = False
        self.textChanged.connect(self._queue_block_styles)
        self.cursorPositionChanged.connect(self._queue_block_styles)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if (event.key() == Qt.Key.Key_Space or event.text() == " ") and self._expand_block_shortcut():
            return
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._handle_code_block_return(event):
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._continue_list_block():
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._toggle_checkbox_at(event.position().toPoint()):
            return
        super().mousePressEvent(event)

    def _expand_block_shortcut(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        block = cursor.block()
        offset = cursor.position() - block.position()
        prefix = block.text()[:offset]
        match = re.match(r'^(\s*)(#{1,3}|[-*+]|\[\]|\[ \]|1\.|"|“|”)$', prefix)
        if not match:
            return False

        indent, marker = match.groups()
        replacements = {
            "*": "- ",
            "-": "- ",
            "+": "- ",
            "[]": "- [ ] ",
            "[ ]": "- [ ] ",
            "1.": "1. ",
            '"': '" ',
            "“": '" ',
            "”": '" ',
        }
        replacement = indent + replacements.get(marker, f"{marker} ")
        cursor.setPosition(block.position())
        cursor.setPosition(block.position() + offset, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
        self.setTextCursor(cursor)
        self._refresh_block_styles()
        return True

    def _handle_code_block_return(self, event) -> bool:
        if not self._is_cursor_inside_code_block():
            return False

        cursor = self.textCursor()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            cursor.insertText("\n")
        else:
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n```\n")
        self.setTextCursor(cursor)
        self._queue_block_styles()
        return True

    def _is_cursor_inside_code_block(self) -> bool:
        cursor = self.textCursor()
        current = cursor.block()
        if current.text().lstrip().startswith("```"):
            return False

        in_code = False
        block = self.document().firstBlock()
        while block.isValid():
            if block == current:
                return in_code
            if block.text().lstrip().startswith("```"):
                in_code = not in_code
            block = block.next()
        return False

    def _continue_list_block(self) -> bool:
        cursor = self.textCursor()
        text = cursor.block().text()
        match = re.match(r"^(\s*)([-*+]|\d+\.|- \[[ xX]\]|\[[ xX]\])\s+(.*)$", text)
        if not match:
            return False
        if not match.group(3).strip():
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            self.setTextCursor(cursor)
            return True
        marker = match.group(2)
        if marker.endswith("."):
            marker = f"{int(marker[:-1]) + 1}."
        elif marker.startswith("- ["):
            marker = "- [ ]"
        cursor.insertText(f"\n{match.group(1)}{marker} ")
        return True

    def _queue_block_styles(self) -> None:
        if self._formatting_blocks:
            return
        self._refresh_block_styles()

    def _refresh_block_styles(self) -> None:
        if self._formatting_blocks:
            return

        self._formatting_blocks = True
        signal_blocker = QSignalBlocker(self)
        active_cursor = self.textCursor()
        cursor_position = active_cursor.position()
        anchor_position = active_cursor.anchor()
        in_code = False
        block = self.document().firstBlock()
        while block.isValid():
            stripped = block.text().lstrip()
            block_format = self._default_block_format()
            if stripped.startswith("```"):
                in_code = not in_code
                block_format.setLineHeight(1, QTextBlockFormat.LineHeightTypes.FixedHeight.value)
                block_format.setTopMargin(0)
                block_format.setBottomMargin(0)
            elif in_code:
                block_format.setBackground(QColor("#eef3fa"))
                block_format.setLeftMargin(14)
                block_format.setRightMargin(14)
                block_format.setTopMargin(3)
                block_format.setBottomMargin(3)
            elif self._checkbox_marker(stripped) is not None:
                block_format.setLeftMargin(22)
                block_format.setRightMargin(4)
                block_format.setTopMargin(3)
                block_format.setBottomMargin(3)
            elif stripped.startswith('" '):
                block_format.setBackground(QColor("#f6f8fb"))
                block_format.setLeftMargin(12)
                block_format.setRightMargin(8)
                block_format.setTopMargin(4)
                block_format.setBottomMargin(4)
            elif re.match(r"^#{1,3}\s*", stripped):
                block_format.setTopMargin(7)
                block_format.setBottomMargin(5)

            block_cursor = QTextCursor(block)
            block_cursor.setBlockFormat(block_format)
            block = block.next()

        restored = self.textCursor()
        restored.setPosition(anchor_position)
        restored.setPosition(cursor_position, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(restored)
        del signal_blocker
        self._formatting_blocks = False

    def _default_block_format(self) -> QTextBlockFormat:
        block_format = QTextBlockFormat()
        block_format.setTopMargin(2)
        block_format.setBottomMargin(2)
        block_format.setLeftMargin(0)
        block_format.setRightMargin(0)
        return block_format

    def refresh_block_styles(self) -> None:
        self._refresh_block_styles()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_code_block_backgrounds(painter)
        painter.end()

        super().paintEvent(event)

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_quote_markers(painter)
        self._paint_checkboxes(painter)
        painter.end()

    def _paint_code_block_backgrounds(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#eef3fa"))
        for top, bottom in self._code_block_ranges():
            rect = QRectF(self.viewport().rect().adjusted(8, 0, -8, 0))
            rect.setTop(top)
            rect.setBottom(bottom)
            painter.drawRoundedRect(rect, 8, 8)

    def _paint_quote_markers(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        block = self.document().firstBlock()
        while block.isValid():
            stripped = block.text().lstrip()
            if stripped.startswith('" '):
                rect = self.cursorRect(QTextCursor(block))
                x = max(9, rect.left() - 8)
                painter.setBrush(QColor("#cfd8e6"))
                painter.drawRoundedRect(x, rect.top() - 1, 3, rect.height() + 4, 1.5, 1.5)
            block = block.next()

    def _paint_checkboxes(self, painter: QPainter) -> None:
        block = self.document().firstBlock()
        while block.isValid():
            marker = self._checkbox_marker(block.text())
            if marker is not None:
                rect = self._checkbox_rect(block)
                checked = marker.lower() in ("- [x]", "[x]")
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(QColor("#9aa6b8") if not checked else QColor("#2f80ff"))
                painter.setBrush(QColor("#2f80ff") if checked else QColor("#ffffff"))
                painter.drawRoundedRect(rect, 3, 3)
                if checked:
                    painter.setPen(QColor("#ffffff"))
                    painter.drawLine(int(rect.left()) + 3, int(rect.center().y()), int(rect.left()) + 6, int(rect.bottom()) - 4)
                    painter.drawLine(int(rect.left()) + 6, int(rect.bottom()) - 4, int(rect.right()) - 3, int(rect.top()) + 4)
            block = block.next()

    def _checkbox_marker(self, text: str) -> str | None:
        match = re.match(r"^\s*(- \[[ xX]\]|\[[ xX]\])\s+", text)
        return match.group(1) if match else None

    def _checkbox_rect(self, block) -> QRectF:
        cursor = QTextCursor(block)
        rect = self.cursorRect(cursor)
        return QRectF(rect.left() - 18, rect.top() + 3, 13, 13)

    def _toggle_checkbox_at(self, point: QPoint) -> bool:
        block = self.document().firstBlock()
        while block.isValid():
            marker = self._checkbox_marker(block.text())
            hit_rect = self._checkbox_rect(block).adjusted(-3, -3, 5, 5)
            if marker is not None and hit_rect.contains(float(point.x()), float(point.y())):
                cursor = QTextCursor(block)
                cursor.setPosition(block.position() + block.text().find(marker))
                cursor.setPosition(cursor.position() + len(marker), QTextCursor.MoveMode.KeepAnchor)
                cursor.insertText(self._toggled_checkbox_marker(marker))
                self.setTextCursor(cursor)
                self._queue_block_styles()
                return True
            block = block.next()
        return False

    def _toggled_checkbox_marker(self, marker: str) -> str:
        checked = marker.lower() in ("- [x]", "[x]")
        if marker.startswith("["):
            return "[ ]" if checked else "[x]"
        return "- [ ]" if checked else "- [x]"

    def _code_block_ranges(self) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        in_code = False
        group_top: int | None = None
        group_bottom: int | None = None
        block = self.document().firstBlock()

        while block.isValid():
            stripped = block.text().lstrip()
            if stripped.startswith("```"):
                if in_code and group_top is not None and group_bottom is not None:
                    ranges.append((group_top, group_bottom))
                    group_top = None
                    group_bottom = None
                in_code = not in_code
                block = block.next()
                continue

            if in_code:
                rect = self.cursorRect(QTextCursor(block))
                if group_top is None:
                    group_top = rect.top() - 5
                group_bottom = rect.bottom() + 5

            block = block.next()

        if in_code and group_top is not None and group_bottom is not None:
            ranges.append((group_top, group_bottom))

        return ranges


class MemoDragHandle(QWidget):
    def __init__(self, item: "MemoCard") -> None:
        super().__init__()
        self._item = item
        self.setFixedSize(14, 20)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.grabMouse()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._item.begin_drag(event.globalPosition().toPoint(), grab_mouse=False)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._item.update_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._item.end_drag()
            self.releaseMouse()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#cdd2db"))
        for row in range(3):
            for col in range(2):
                painter.drawEllipse(col * 6 + 1, row * 6 + 1, 3, 3)
        painter.end()


class MemoCard(QFrame):
    H_MARGIN = 24
    V_MARGIN = 24
    MIN_HEIGHT = 88
    CHROME_WIDTH = 14 + 28 + 16 + H_MARGIN
    BODY_MAX_LINES = 2

    def __init__(self, memo: Memo, parent_view: "MemoView") -> None:
        super().__init__()
        self._memo = memo
        self._parent_view = parent_view
        self._drag_active = False
        self.setObjectName("memoItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)

        self._handle = MemoDragHandle(self)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(5)

        self._title = QLabel(self._display_title())
        self._title.setObjectName("memoItemTitle")
        self._title.setWordWrap(False)
        self._title.installEventFilter(self)

        self._body = QLabel(self._display_body())
        self._body.setObjectName("memoItemBody")
        self._body.setWordWrap(True)
        self._body.installEventFilter(self)

        self._date = QLabel(self._display_date())
        self._date.setObjectName("memoItemDate")
        self._date.installEventFilter(self)

        text_col.addWidget(self._title)
        text_col.addWidget(self._body)
        text_col.addWidget(self._date)

        delete_btn = QPushButton("x")
        delete_btn.setObjectName("memoDeleteButton")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self._parent_view.delete_memo(self))

        layout.addWidget(self._handle, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_col, 1)
        layout.addWidget(delete_btn, 0, Qt.AlignmentFlag.AlignTop)

    @property
    def memo_id(self) -> int:
        return self._memo.id

    def set_card_width(self, width: int) -> None:
        width = max(160, width)
        text_width = max(80, width - self.CHROME_WIDTH)

        title_metrics = self._title.fontMetrics()
        body_metrics = self._body.fontMetrics()
        date_metrics = self._date.fontMetrics()

        self._title.setText(title_metrics.elidedText(self._display_title(), Qt.TextElideMode.ElideRight, text_width))
        self._body.setText(self._elided_body(text_width))

        title_height = title_metrics.height() + 2
        body_lines = max(1, self._body.text().count("\n") + 1) if self._body.text() else 0
        body_height = body_lines * body_metrics.lineSpacing()
        date_height = date_metrics.height() + 2
        content_height = title_height + body_height + date_height + 10

        self._title.setFixedSize(text_width, title_height)
        self._body.setFixedSize(text_width, body_height)
        self._date.setFixedSize(text_width, date_height)
        self.setFixedSize(width, max(self.MIN_HEIGHT, content_height + self.V_MARGIN))

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched in (self._title, self._body, self._date):
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._parent_view.open_editor(self._memo)
                return True
        return super().eventFilter(watched, event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_active:
                self.end_drag()
                event.accept()
                return
            self._parent_view.open_editor(self._memo)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def begin_drag(self, global_pos: QPoint, grab_mouse: bool = True) -> None:
        if grab_mouse:
            self.grabMouse()
        self._drag_active = True
        self.setProperty("dragging", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self._parent_view.begin_drag(self, global_pos)

    def update_drag(self, global_pos: QPoint) -> None:
        self._parent_view.update_drag(global_pos)

    def end_drag(self) -> None:
        self._drag_active = False
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if self.mouseGrabber() is self:
            self.releaseMouse()
        self._parent_view.end_drag()

    def _display_title(self) -> str:
        title = self._memo.title.strip()
        if title:
            return title
        first_line = next(
            (
                preview_line(line)
                for line in self._memo.body.splitlines()
                if preview_line(line) and not line.strip().startswith("```")
            ),
            "",
        )
        return first_line or "제목 없는 메모"

    def _display_body(self) -> str:
        body_lines = [
            preview_line(line)
            for line in self._memo.body.splitlines()
            if preview_line(line) and not line.strip().startswith("```")
        ]
        preview = " ".join(body_lines[1:] if len(body_lines) > 1 else body_lines)
        return preview

    def _elided_body(self, width: int) -> str:
        text = self._display_body()
        if not text:
            return ""

        metrics = self._body.fontMetrics()
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if metrics.horizontalAdvance(candidate) <= width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = word
            else:
                lines.append(metrics.elidedText(word, Qt.TextElideMode.ElideRight, width))
                current = ""
            if len(lines) == self.BODY_MAX_LINES:
                break

        if current and len(lines) < self.BODY_MAX_LINES:
            lines.append(current)

        consumed_words = " ".join(lines).replace("...", "").split()
        if len(consumed_words) < len(text.split()) and lines:
            lines[-1] = metrics.elidedText(lines[-1] + " ...", Qt.TextElideMode.ElideRight, width)

        return "\n".join(lines[: self.BODY_MAX_LINES])

    def _display_date(self) -> str:
        value = self._memo.updated_at or self._memo.created_at
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
        except ValueError:
            return value

        now = datetime.now(timezone.utc).astimezone()
        if dt.date() == now.date():
            return dt.strftime("오늘 %p %-I:%M").replace("AM", "오전").replace("PM", "오후")
        return dt.strftime("%-m월 %-d일 %p %-I:%M").replace("AM", "오전").replace("PM", "오후")


class MemoEditor(QFrame):
    def __init__(self, parent_view: "MemoView") -> None:
        super().__init__()
        self._parent_view = parent_view
        self._memo: Memo | None = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self.save_now)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("memoEditor")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        back_btn = QPushButton("‹")
        back_btn.setObjectName("memoBackButton")
        back_btn.setFixedSize(30, 30)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self._parent_view.show_list)

        self._save_state = QLabel("저장됨")
        self._save_state.setObjectName("memoSaveState")

        top_row.addWidget(back_btn)
        top_row.addStretch(1)
        top_row.addWidget(self._save_state)

        self._editor = MemoTextEdit()
        self._editor.setObjectName("memoTextEdit")
        self._editor.setPlaceholderText("Markdown으로 메모를 작성하세요...")
        self._editor.setAcceptRichText(False)
        self._editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self._editor.textChanged.connect(self._schedule_save)
        self._highlighter = MarkdownHighlighter(self._editor.document())

        layout.addLayout(top_row)
        layout.addWidget(self._editor, 1)

    def edit(self, memo: Memo) -> None:
        self._memo = memo
        self._save_timer.stop()
        self._editor.blockSignals(True)
        self._editor.setPlainText(memo.body)
        self._editor.blockSignals(False)
        self._editor.refresh_block_styles()
        self._save_state.setText("저장됨")
        QTimer.singleShot(0, self._editor.setFocus)

    def save_now(self) -> None:
        if self._memo is None:
            return
        body = self._editor.toPlainText()
        title = next(
            (
                preview_line(line)
                for line in body.splitlines()
                if preview_line(line) and not line.strip().startswith("```")
            ),
            "",
        )
        updated = memo_store.update(self._memo.id, title[:80], body)
        if updated is not None:
            self._memo = updated
        self._save_state.setText("저장됨")
        self._parent_view.refresh_list()

    def _schedule_save(self) -> None:
        self._save_state.setText("저장 중...")
        self._save_timer.start()


class MemoView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("memoView")
        self._items: list[MemoCard] = []
        self._drag_item: MemoCard | None = None
        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list_page = QWidget()
        list_layout = QVBoxLayout(self._list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self._build_header())

        self._scroll = QScrollArea()
        self._scroll.setObjectName("memoScrollArea")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("memoListContent")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(LIST_MARGIN_X, 12, LIST_MARGIN_X, 10)
        self._list_layout.setSpacing(ITEM_GAP)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list_widget)
        list_layout.addWidget(self._scroll, 1)
        list_layout.addWidget(self._build_add_bar())

        self._editor = MemoEditor(self)
        layout.addWidget(self._list_page)
        layout.addWidget(self._editor)
        self._editor.hide()

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("memoHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(17, 10, 17, 10)
        layout.setSpacing(7)

        note_icon = QLabel()
        note_icon.setFixedSize(20, 20)
        note_icon.setPixmap(tinted_icon("memo.png", QColor("#20242c"), QSize(17, 17)).pixmap(17, 17))

        self._count_label = QLabel("내 메모 0")
        self._count_label.setObjectName("memoCountLabel")

        layout.addWidget(note_icon)
        layout.addWidget(self._count_label)
        layout.addStretch(1)
        return frame

    def _build_add_bar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("memoAddBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self._add_btn = QPushButton("새로운 메모")
        self._add_btn.setObjectName("memoAddButton")
        self._add_btn.setIcon(tinted_icon("memo.png", QColor("#667085"), QSize(17, 17)))
        self._add_btn.setIconSize(QSize(17, 17))
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self.create_memo)
        layout.addWidget(self._add_btn)
        return frame

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        QTimer.singleShot(0, self.sync_item_sizes)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self.sync_item_sizes)

    def create_memo(self) -> None:
        memo = memo_store.add("", "")
        self.open_editor(memo)

    def open_editor(self, memo: Memo) -> None:
        self._list_page.hide()
        self._editor.show()
        self._editor.edit(memo)

    def show_list(self) -> None:
        self._editor.save_now()
        self.refresh_list()
        self._editor.hide()
        self._list_page.show()

    def refresh_list(self) -> None:
        memos = memo_store.get_all()
        self._clear_items()
        for memo in memos:
            self._insert_item(memo)
        self._count_label.setText(f"내 메모 {len(memos)}")

    def delete_memo(self, item: MemoCard) -> None:
        memo_store.delete(item.memo_id)
        self.refresh_list()

    def begin_drag(self, item: MemoCard, global_pos: QPoint) -> None:
        self._drag_item = item
        self.update_drag(global_pos)

    def update_drag(self, global_pos: QPoint) -> None:
        if self._drag_item is None or len(self._items) < 2:
            return
        old_index = self._items.index(self._drag_item)
        new_index = self._index_for_global_y(global_pos)
        if new_index == old_index:
            return
        self._items.pop(old_index)
        self._items.insert(new_index, self._drag_item)
        self._list_layout.removeWidget(self._drag_item)
        self._list_layout.insertWidget(new_index, self._drag_item, 0, Qt.AlignmentFlag.AlignTop)
        self.sync_item_sizes()

    def end_drag(self) -> None:
        if self._drag_item is None:
            return
        memo_store.reorder_many([item.memo_id for item in self._items])
        self._drag_item = None

    def sync_item_sizes(self) -> None:
        if not hasattr(self, "_scroll"):
            return
        width = self._scroll.viewport().width() - (LIST_MARGIN_X * 2)
        for item in self._items:
            item.set_card_width(width)
        self._list_widget.setMinimumWidth(self._scroll.viewport().width())

    def _insert_item(self, memo: Memo) -> None:
        item = MemoCard(memo, self)
        self._items.append(item)
        self._list_layout.insertWidget(len(self._items) - 1, item, 0, Qt.AlignmentFlag.AlignTop)
        QTimer.singleShot(0, self.sync_item_sizes)

    def _clear_items(self) -> None:
        for item in self._items:
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def _index_for_global_y(self, global_pos: QPoint) -> int:
        local_y = self._list_widget.mapFromGlobal(global_pos).y()
        for index, item in enumerate(self._items):
            if local_y < item.geometry().center().y():
                return index
        return max(0, len(self._items) - 1)
