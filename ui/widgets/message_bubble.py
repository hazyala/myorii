from __future__ import annotations

from dataclasses import dataclass
import re

from PyQt6.QtCore import QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPen, QPixmap, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.assets import asset_path, tinted_icon


@dataclass(frozen=True)
class MessageAttachment:
    path: str
    name: str
    suffix: str
    is_image: bool


class CodeHighlighter(QSyntaxHighlighter):
    KEYWORDS = {
        "False",
        "None",
        "True",
        "and",
        "as",
        "async",
        "await",
        "break",
        "case",
        "class",
        "const",
        "continue",
        "def",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "function",
        "if",
        "import",
        "in",
        "let",
        "return",
        "try",
        "var",
        "while",
    }

    def __init__(self, document) -> None:
        super().__init__(document)
        self._ranges: list[tuple[int, int]] = []
        self._code_format = QTextCharFormat()
        self._code_format.setFontFamily("Menlo")
        self._code_format.setFontFixedPitch(True)
        self._code_format.setFontPointSize(12)
        self._keyword_format = QTextCharFormat(self._code_format)
        self._keyword_format.setForeground(QColor("#2f80ff"))
        self._string_format = QTextCharFormat(self._code_format)
        self._string_format.setForeground(QColor("#16845b"))
        self._comment_format = QTextCharFormat(self._code_format)
        self._comment_format.setForeground(QColor("#7c8797"))

    def set_ranges(self, ranges: list[tuple[int, int]]) -> None:
        self._ranges = ranges
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        block_start = self.currentBlock().position()
        block_end = block_start + len(text)
        for start, end in self._ranges:
            overlap_start = max(start, block_start)
            overlap_end = min(end, block_end)
            if overlap_start >= overlap_end:
                continue

            local_start = overlap_start - block_start
            length = overlap_end - overlap_start
            self.setFormat(local_start, length, self._code_format)
            self._highlight_syntax(text, local_start, length)

    def _highlight_syntax(self, text: str, start: int, length: int) -> None:
        fragment = text[start : start + length]
        for match in re.finditer(r"\b(" + "|".join(self.KEYWORDS) + r")\b", fragment):
            self.setFormat(start + match.start(), match.end() - match.start(), self._keyword_format)
        for match in re.finditer(r"(['\"])(?:\\.|(?!\1).)*\1", fragment):
            self.setFormat(start + match.start(), match.end() - match.start(), self._string_format)
        for match in re.finditer(r"(#|//).*", fragment):
            self.setFormat(start + match.start(), match.end() - match.start(), self._comment_format)


class CodeTextBrowser(QTextBrowser):
    code_copied = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._code_ranges: list[tuple[int, int, str]] = []
        self._highlighter = CodeHighlighter(self.document())
        self.setStyleSheet(
            """
            QTextBrowser {
                background: transparent;
                border: none;
                color: #222833;
                font-size: 13px;
            }
            pre {
                background-color: #f3f6fb;
                border-radius: 8px;
                margin-top: 6px;
                margin-bottom: 6px;
                padding: 8px;
                white-space: pre-wrap;
            }
            code {
                background-color: #f3f6fb;
                border-radius: 5px;
                font-family: Menlo;
                font-size: 12px;
            }
            """
        )

    def set_code_ranges(self, ranges: list[tuple[int, int, str]]) -> None:
        self._code_ranges = ranges
        self._highlighter.set_ranges([(start, end) for start, end, _text in ranges])

    def mousePressEvent(self, event) -> None:  # noqa: N802
        copied = self._copy_code_at(event.position().toPoint())
        if copied:
            return
        super().mousePressEvent(event)

    def _copy_code_at(self, position) -> bool:
        cursor = self.cursorForPosition(position)
        index = cursor.position()
        for start, end, code in self._code_ranges:
            if start <= index <= end:
                QApplication.clipboard().setText(code)
                self.code_copied.emit(code)
                return True
        return False


class CodeBlockWidget(QFrame):
    code_copied = pyqtSignal(str)

    def __init__(self, code: str) -> None:
        super().__init__()
        self._code = code
        self.setObjectName("codeBlockFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "background: rgba(232, 238, 247, 218);"
            "border: 1px solid rgba(255, 255, 255, 190);"
            "border-radius: 8px;"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(70, 88, 116, 28))
        self.setGraphicsEffect(shadow)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 8, 10)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addStretch(1)

        copy = QPushButton()
        copy.setObjectName("codeCopyButton")
        copy.setIcon(self._copy_icon())
        copy.setIconSize(QSize(16, 16))
        copy.setFixedSize(26, 24)
        copy.setFlat(True)
        copy.setCursor(Qt.CursorShape.PointingHandCursor)
        copy.setStyleSheet("background: transparent; border: none; padding: 0;")
        copy.clicked.connect(self.copy_code)
        header.addWidget(copy)
        layout.addLayout(header)

        self._body = CodeTextBrowser()
        self._body.setPlainText(code)
        self._body.set_code_ranges([(0, len(code), code)])
        self._body.setCursor(Qt.CursorShape.PointingHandCursor)
        self._body.setStyleSheet("background: transparent; border: none;")
        self._body.viewport().setStyleSheet("background: transparent;")
        self._body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._body.document().setDocumentMargin(0)
        layout.addWidget(self._body)
        self._sync_height()

    def copy_code(self) -> None:
        QApplication.clipboard().setText(self._code)
        self.code_copied.emit(self._code)

    def _copy_icon(self) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(61, 75, 95, 85), 1.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(5, 2, 8, 9, 2, 2)
        painter.setPen(QPen(QColor("#3d4b5f"), 1.7))
        painter.drawRoundedRect(2, 5, 9, 9, 2, 2)
        painter.end()
        return QIcon(pixmap)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.copy_code()
        super().mousePressEvent(event)

    def update_width(self, width: int) -> None:
        self.setFixedWidth(width)
        self._sync_height()

    def _sync_height(self) -> None:
        document = self._body.document()
        document.setTextWidth(max(80, self.width() - 20))
        height = max(24, int(document.size().height()) + 8)
        self._body.setFixedHeight(height)


class UserAttachmentPreview(QFrame):
    MIN_WIDTH = 132
    MAX_WIDTH = 178

    def __init__(self, attachment: MessageAttachment) -> None:
        super().__init__()
        self._attachment = attachment
        self.setObjectName("userAttachmentPreview")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(38)
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 9, 5)
        layout.setSpacing(7)

        thumbnail = QLabel()
        thumbnail.setObjectName("userAttachmentThumbnail")
        thumbnail.setFixedSize(28, 28)
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if attachment.is_image:
            pixmap = QPixmap(attachment.path)
            if not pixmap.isNull():
                thumbnail.setPixmap(
                    pixmap.scaled(
                        thumbnail.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                thumbnail.setText("IMG")
        else:
            thumbnail.setText(attachment.suffix.lstrip(".").upper()[:4] or "FILE")

        name = QLabel(attachment.name)
        name.setObjectName("userAttachmentName")
        name.setToolTip(attachment.path)
        name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(thumbnail)
        layout.addWidget(name, 1)

    def update_width(self, max_width: int) -> None:
        next_width = max(self.MIN_WIDTH, min(self.MAX_WIDTH, max_width))
        self.setFixedWidth(next_width)
        name = self.findChild(QLabel, "userAttachmentName")
        if name is None:
            return
        metrics = QFontMetrics(name.font())
        available = max(44, next_width - 54)
        name.setText(metrics.elidedText(self._attachment.name, Qt.TextElideMode.ElideRight, available))


class MessageBubble(QWidget):
    code_copied = pyqtSignal(str)

    WIDTH_RATIO = 0.94
    ASSISTANT_SIDE_RESERVE = 62
    USER_SIDE_RESERVE = 62
    BUBBLE_HORIZONTAL_PADDING = 24
    MIN_BODY_WIDTH = 96

    def __init__(
        self,
        role: str,
        text: str = "",
        attachments: list[MessageAttachment] | None = None,
    ) -> None:
        super().__init__()
        self._role = role
        self._text = text
        self._attachments = attachments or []
        self._available_width = 320
        self._indicator_step = 0
        self._attachment_previews: list[UserAttachmentPreview] = []
        self._attachment_container: QWidget | None = None
        self._attachment_rows_layout: QVBoxLayout | None = None
        self._rendered_code_blocks: list[CodeBlockWidget] = []
        self.setObjectName(f"{role}MessageRow")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._bubble = QFrame()
        self._bubble.setObjectName(f"{role}MessageBubble")
        self._bubble.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        if role == "user":
            self._bubble.setStyleSheet("background: #2f80ff; border-radius: 14px;")
        else:
            self._bubble.setStyleSheet("background: #ffffff; border: none; border-radius: 14px;")

        self._bubble_layout = QVBoxLayout(self._bubble)
        self._bubble_layout.setContentsMargins(12, 9, 12, 9)
        self._bubble_layout.setSpacing(8)

        if role == "user":
            self._body = QLabel()
            self._body.setWordWrap(True)
            self._body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._body.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
            self._body.setStyleSheet(
                "background: transparent; border: none; color: #ffffff; font-size: 13px;"
            )
        else:
            self._body = CodeTextBrowser()
            self._body.setFrameShape(QFrame.Shape.NoFrame)
            self._body.setOpenExternalLinks(True)
            self._body.setReadOnly(True)
            self._body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._body.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._body.document().setDocumentMargin(0)
            self._body.code_copied.connect(self.code_copied.emit)
        self._body.setObjectName(f"{role}MessageBody")
        self._bubble_layout.addWidget(self._body)

        self._indicator = self._build_indicator() if role == "assistant" else None
        if self._indicator is not None:
            self._bubble_layout.addWidget(self._indicator)
            self._indicator.hide()

        if role == "user":
            row.addStretch(1)
            self._user_stack = QWidget()
            self._user_stack.setObjectName("userMessageStack")
            stack_layout = QVBoxLayout(self._user_stack)
            stack_layout.setContentsMargins(0, 0, 0, 0)
            stack_layout.setSpacing(5)
            if self._attachments:
                self._attachment_container = QWidget()
                self._attachment_container.setObjectName("userAttachmentGrid")
                self._attachment_rows_layout = QVBoxLayout(self._attachment_container)
                self._attachment_rows_layout.setContentsMargins(0, 0, 0, 0)
                self._attachment_rows_layout.setSpacing(5)
                for attachment in self._attachments:
                    preview = UserAttachmentPreview(attachment)
                    self._attachment_previews.append(preview)
                stack_layout.addWidget(self._attachment_container)
            stack_layout.addWidget(self._bubble, 0, Qt.AlignmentFlag.AlignRight)
            row.addWidget(self._user_stack)
        else:
            avatar = QLabel()
            avatar.setObjectName("assistantAvatar")
            avatar.setFixedSize(28, 28)
            avatar.setPixmap(
                QPixmap(str(asset_path("characters", "myorii_profile.png"))).scaled(
                    avatar.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            row.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(self._bubble)
            row.addStretch(1)

        self._indicator_timer = QTimer(self)
        self._indicator_timer.setInterval(300)
        self._indicator_timer.timeout.connect(self._advance_indicator)
        self.update_available_width(self._available_width)
        self.set_text(text)

    def update_available_width(self, available_width: int) -> None:
        self._available_width = max(available_width, self.MIN_BODY_WIDTH)
        body_width = self._body_width()
        self._bubble.setMaximumWidth(body_width + self.BUBBLE_HORIZONTAL_PADDING)
        if isinstance(self._body, QLabel):
            self._body.setFixedWidth(self._user_body_width(body_width))
        self._layout_attachment_previews(body_width)
        for block in self._rendered_code_blocks:
            block.update_width(body_width)
        self._sync_height()

    def show_loading_indicator(self) -> None:
        if self._indicator is None:
            return
        self._body.hide()
        self._indicator.show()
        self._indicator_step = 0
        self._advance_indicator()
        self._indicator_timer.start()

    def hide_loading_indicator(self) -> None:
        if self._indicator is None:
            return
        self._indicator_timer.stop()
        self._indicator.hide()
        self._body.show()
        for dot in self._indicator.findChildren(QLabel):
            dot.setContentsMargins(0, 6, 0, 0)

    def append_token(self, token: str) -> None:
        self.hide_loading_indicator()
        self._text += token
        self._set_plain_text(self._text)
        self._sync_height()

    def set_text(self, text: str) -> None:
        self.hide_loading_indicator()
        self._text = text
        self._set_plain_text(text)
        self._sync_height()

    def render_markdown(self) -> None:
        self.hide_loading_indicator()
        if isinstance(self._body, CodeTextBrowser):
            self._render_markdown_blocks()
        self._sync_height()

    def _set_plain_text(self, text: str) -> None:
        if isinstance(self._body, QTextBrowser):
            self._clear_code_blocks()
            self._body.setPlainText(text)
            if isinstance(self._body, CodeTextBrowser):
                self._body.set_code_ranges([])
        else:
            self._body.setText(text)
            self._bubble.setVisible(bool(text.strip()))

    def _body_width(self) -> int:
        reserve = self.ASSISTANT_SIDE_RESERVE if self._role == "assistant" else self.USER_SIDE_RESERVE
        usable = max(self.MIN_BODY_WIDTH, self._available_width - reserve)
        return max(self.MIN_BODY_WIDTH, int(usable * self.WIDTH_RATIO))

    def _user_body_width(self, max_width: int) -> int:
        if not isinstance(self._body, QLabel):
            return max_width
        lines = self._text.splitlines() or [self._text]
        metrics = QFontMetrics(self._body.font())
        ideal = max((metrics.horizontalAdvance(line) for line in lines), default=0) + 2
        return max(24, min(max_width, ideal))

    def _layout_attachment_previews(self, body_width: int) -> None:
        if self._attachment_container is None or self._attachment_rows_layout is None:
            return

        while self._attachment_rows_layout.count():
            item = self._attachment_rows_layout.takeAt(0)
            row_widget = item.widget()
            if row_widget is not None:
                row_widget.deleteLater()

        spacing = 6
        columns = max(1, min(2, (body_width + spacing) // (UserAttachmentPreview.MIN_WIDTH + spacing)))
        card_width = max(
            UserAttachmentPreview.MIN_WIDTH,
            min(UserAttachmentPreview.MAX_WIDTH, (body_width - spacing * (columns - 1)) // columns),
        )

        self._attachment_container.setFixedWidth(body_width)
        for offset in range(0, len(self._attachment_previews), columns):
            row_widget = QWidget()
            row_widget.setObjectName("userAttachmentRow")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(spacing)
            row_layout.addStretch(1)
            for preview in self._attachment_previews[offset : offset + columns]:
                preview.update_width(card_width)
                row_layout.addWidget(preview)
            self._attachment_rows_layout.addWidget(row_widget)

    def _sync_height(self) -> None:
        body_width = self._body_width()
        if not isinstance(self._body, QTextBrowser):
            self._body.setFixedWidth(self._user_body_width(body_width))
            self._body.adjustSize()
            return

        document = self._body.document()
        document.setTextWidth(body_width)
        height = max(22, int(document.size().height()) + 2)
        self._body.setFixedSize(body_width, height)

    def _build_indicator(self) -> QWidget:
        indicator = QWidget()
        indicator.setObjectName("pawLoadingIndicator")
        layout = QHBoxLayout(indicator)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        icon = tinted_icon("foot.png", QColor("#f04452"), QSize(14, 14))
        for _index in range(3):
            paw = QLabel()
            paw.setObjectName("pawLoadingDot")
            paw.setFixedSize(16, 22)
            paw.setPixmap(icon.pixmap(14, 14))
            paw.setContentsMargins(0, 6, 0, 0)
            paw.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(paw)
        return indicator

    def _advance_indicator(self) -> None:
        if self._indicator is None:
            return
        dots = self._indicator.findChildren(QLabel)
        for index, dot in enumerate(dots):
            top = 0 if index == self._indicator_step % len(dots) else 6
            dot.setContentsMargins(0, top, 0, 6 - top)
        self._indicator_step += 1

    def _code_ranges(self) -> list[tuple[int, int, str]]:
        plain_text = self._body.toPlainText() if isinstance(self._body, QTextBrowser) else ""
        snippets = self._extract_code_snippets()
        ranges: list[tuple[int, int, str]] = []
        search_from = 0
        for snippet in snippets:
            if not snippet:
                continue
            index = plain_text.find(snippet, search_from)
            if index < 0:
                index = plain_text.find(snippet)
            if index < 0:
                continue
            ranges.append((index, index + len(snippet), snippet))
            search_from = index + len(snippet)
        return ranges

    def _render_markdown_blocks(self) -> None:
        self._clear_code_blocks()
        if not isinstance(self._body, CodeTextBrowser):
            return

        segments = self._markdown_segments()
        text_parts = [text for kind, text in segments if kind == "text" and text.strip()]
        self._body.setMarkdown("\n\n".join(text_parts))
        self._body.set_code_ranges([])
        for kind, text in segments:
            if kind != "code":
                continue
            block = CodeBlockWidget(text)
            block.code_copied.connect(self.code_copied.emit)
            block.update_width(self._body_width())
            self._rendered_code_blocks.append(block)
            self._bubble_layout.addWidget(block)

    def _clear_code_blocks(self) -> None:
        for block in self._rendered_code_blocks:
            self._bubble_layout.removeWidget(block)
            block.deleteLater()
        self._rendered_code_blocks.clear()

    def _markdown_segments(self) -> list[tuple[str, str]]:
        segments: list[tuple[str, str]] = []
        position = 0
        fenced_pattern = re.compile(r"```[^\n`]*\n(.*?)```", flags=re.DOTALL)
        for match in fenced_pattern.finditer(self._text):
            self._append_inline_segments(segments, self._text[position : match.start()])
            for code in self._split_code_units(match.group(1).strip("\n")):
                segments.append(("code", code))
            position = match.end()
        self._append_inline_segments(segments, self._text[position:])
        return segments

    def _split_code_units(self, code: str) -> list[str]:
        lines = code.splitlines()
        starts = self._code_unit_starts(lines)
        if len(starts) <= 1:
            return [code]

        blocks: list[str] = []
        for offset, start in enumerate(starts):
            end = starts[offset + 1] if offset + 1 < len(starts) else len(lines)
            block = self._clean_code_unit("\n".join(lines[start:end]).strip("\n"))
            if block:
                blocks.append(block)
        return blocks or [code]

    def _code_unit_starts(self, lines: list[str]) -> list[int]:
        numbered_starts = [
            index
            for index, line in enumerate(lines)
            if re.match(r"^\s*\d+[\.)]\s+\*{0,2}[\w가-힣][\w가-힣_]*\s*(?:\(|:|->|\*{0,2}\s*$)", line)
        ]
        if len(numbered_starts) > 1:
            return numbered_starts

        declaration_starts = [
            index
            for index, line in enumerate(lines)
            if re.match(r"^(async\s+def|def|class|function)\s+\w+", line)
        ]
        if len(declaration_starts) > 1:
            return declaration_starts

        bullet_starts = [
            index
            for index, line in enumerate(lines)
            if re.match(r"^\s*[-*]\s+\*{0,2}[\w가-힣][\w가-힣_]*\s*(?:\(|:|->|\*{0,2}\s*$)", line)
        ]
        return bullet_starts

    def _append_inline_segments(self, segments: list[tuple[str, str]], text: str) -> None:
        if self._append_detected_code_list_segments(segments, text):
            return
        if self._append_detected_technical_line_segments(segments, text):
            return

        position = 0
        for match in re.finditer(r"`([^`\n]+)`", text):
            plain = text[position : match.start()]
            if plain:
                segments.append(("text", plain))
            segments.append(("code", match.group(1)))
            position = match.end()
        rest = text[position:]
        if rest:
            segments.append(("text", rest))

    def _append_detected_code_list_segments(
        self,
        segments: list[tuple[str, str]],
        text: str,
    ) -> bool:
        lines = text.splitlines()
        starts = self._code_unit_starts(lines)
        if len(starts) <= 1:
            return False

        if starts[0] > 0:
            prefix = "\n".join(lines[: starts[0]]).strip("\n")
            if prefix:
                segments.append(("text", prefix))

        for offset, start in enumerate(starts):
            end = starts[offset + 1] if offset + 1 < len(starts) else len(lines)
            block = self._clean_code_unit("\n".join(lines[start:end]).strip("\n"))
            if block:
                segments.append(("code", block))
        return True

    def _append_detected_technical_line_segments(
        self,
        segments: list[tuple[str, str]],
        text: str,
    ) -> bool:
        lines = text.splitlines()
        if len(lines) <= 1:
            line = text.strip()
            if self._is_technical_line(line):
                segments.append(("code", self._clean_technical_line(line)))
                return True
            return False

        changed = False
        pending_text: list[str] = []
        for line in lines:
            stripped = line.strip()
            if self._is_technical_line(stripped):
                if pending_text:
                    segments.append(("text", "\n".join(pending_text).strip("\n")))
                    pending_text.clear()
                segments.append(("code", self._clean_technical_line(stripped)))
                changed = True
            else:
                pending_text.append(line)

        if pending_text:
            segments.append(("text", "\n".join(pending_text).strip("\n")))
        return changed

    def _is_technical_line(self, line: str) -> bool:
        candidate = self._clean_technical_line(line)
        if not candidate or len(candidate) > 180:
            return False
        if re.search(r"[가-힣]\s+[가-힣]", candidate):
            return False

        filename = r"[\w.-]+\.(?:py|js|jsx|ts|tsx|java|kt|swift|go|rs|rb|php|css|scss|html|xml|json|ya?ml|md|txt|sh|sql)"
        command = r"(?:git|npm|yarn|pnpm|node|python3?|pip|uv|brew|ollama|docker|kubectl|curl|ssh|cd|ls|mkdir|cp|mv|rm|chmod)\b"
        function = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\([^()\n]*\)(?:\s*->\s*[\w\[\]., |]+)?"
        identifier = r"(?:[A-Z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*|[a-z]+(?:_[a-z0-9]+)+|[a-z]+[A-Z][A-Za-z0-9]*|[A-Z_][A-Z0-9_]{2,})"
        path = r"(?:\.{1,2}/|~/|/)[^\s]+"
        return any(
            re.fullmatch(pattern, candidate)
            for pattern in (filename, command + r".*", function + r"\s*:?", identifier, path)
        )

    def _clean_technical_line(self, line: str) -> str:
        cleaned = re.sub(r"^\s*(?:\d+[\.)]|[-*])\s+", "", line.strip())
        cleaned = cleaned.strip("` ")
        return cleaned

    def _clean_code_unit(self, block: str) -> str:
        lines = block.splitlines()
        if not lines:
            return block

        lines[0] = re.sub(r"^\s*(?:\d+[\.)]|[-*])\s+", "", lines[0])
        lines[0] = re.sub(r"^\*\*(.+?)\*\*(?=\s*(?:\(|:|->|$))", r"\1", lines[0])
        return "\n".join(lines).strip("\n")

    def _extract_code_snippets(self) -> list[str]:
        snippets: list[str] = []
        fenced_spans: list[tuple[int, int]] = []
        for match in re.finditer(r"```([^\n`]*)\n(.*?)```", self._text, flags=re.DOTALL):
            fenced_spans.append(match.span())
            snippets.append(match.group(2).strip("\n"))

        masked = list(self._text)
        for start, end in fenced_spans:
            for index in range(start, end):
                masked[index] = " "
        for match in re.finditer(r"`([^`\n]+)`", "".join(masked)):
            snippets.append(match.group(1))
        return snippets
