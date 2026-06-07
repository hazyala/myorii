from __future__ import annotations

import re

from PyQt6.QtCore import QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.assets import asset_path, tinted_icon


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
        self._code_format.setBackground(QColor("#f3f6fb"))
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


class MessageBubble(QWidget):
    code_copied = pyqtSignal(str)

    WIDTH_RATIO = 0.82
    ASSISTANT_SIDE_RESERVE = 42
    BUBBLE_HORIZONTAL_PADDING = 24
    MIN_BODY_WIDTH = 96

    def __init__(self, role: str, text: str = "") -> None:
        super().__init__()
        self._role = role
        self._text = text
        self._available_width = 320
        self._indicator_step = 0
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
            self._bubble.setStyleSheet(
                "background: #ffffff; border: 1px solid rgba(222, 227, 235, 170); border-radius: 14px;"
            )

        self._bubble_layout = QVBoxLayout(self._bubble)
        self._bubble_layout.setContentsMargins(12, 9, 12, 9)
        self._bubble_layout.setSpacing(0)

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
            row.addWidget(self._bubble)
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
        self._indicator_timer.setInterval(150)
        self._indicator_timer.timeout.connect(self._advance_indicator)
        self.update_available_width(self._available_width)
        self.set_text(text)

    def update_available_width(self, available_width: int) -> None:
        self._available_width = max(available_width, self.MIN_BODY_WIDTH)
        body_width = self._body_width()
        self._bubble.setMaximumWidth(body_width + self.BUBBLE_HORIZONTAL_PADDING)
        if isinstance(self._body, QLabel):
            self._body.setMaximumWidth(body_width)
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
            self._body.setMarkdown(self._text)
            self._body.set_code_ranges(self._code_ranges())
        self._sync_height()

    def _set_plain_text(self, text: str) -> None:
        if isinstance(self._body, QTextBrowser):
            self._body.setPlainText(text)
            if isinstance(self._body, CodeTextBrowser):
                self._body.set_code_ranges([])
        else:
            self._body.setText(text)

    def _body_width(self) -> int:
        reserve = self.ASSISTANT_SIDE_RESERVE if self._role == "assistant" else 0
        usable = max(self.MIN_BODY_WIDTH, self._available_width - reserve)
        return max(self.MIN_BODY_WIDTH, int(usable * self.WIDTH_RATIO))

    def _sync_height(self) -> None:
        body_width = self._body_width()
        if not isinstance(self._body, QTextBrowser):
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
