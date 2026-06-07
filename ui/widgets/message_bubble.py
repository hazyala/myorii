from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget

from ui.assets import asset_path


class MessageBubble(QWidget):
    BODY_MAX_WIDTH = 264

    def __init__(self, role: str, text: str = "") -> None:
        super().__init__()
        self._role = role
        self._text = text
        self.setObjectName(f"{role}MessageRow")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        bubble = QFrame()
        bubble.setObjectName(f"{role}MessageBubble")
        bubble.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(self.BODY_MAX_WIDTH + 24)
        if role == "user":
            bubble.setStyleSheet("background: #2f80ff; border-radius: 14px;")
        else:
            bubble.setStyleSheet(
                "background: #ffffff; border: 1px solid rgba(222, 227, 235, 170); border-radius: 14px;"
            )

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 9, 12, 9)
        bubble_layout.setSpacing(0)

        if role == "user":
            self._body = QLabel()
            self._body.setWordWrap(True)
            self._body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._body.setMaximumWidth(self.BODY_MAX_WIDTH)
            self._body.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        else:
            self._body = QTextBrowser()
            self._body.setFrameShape(QFrame.Shape.NoFrame)
            self._body.setOpenExternalLinks(True)
            self._body.setReadOnly(True)
            self._body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._body.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._body.document().setDocumentMargin(0)
        self._body.setObjectName(f"{role}MessageBody")
        self._body.setStyleSheet(
            "background: transparent; border: none; font-size: 13px; color: "
            + ("#ffffff;" if role == "user" else "#222833;")
        )
        bubble_layout.addWidget(self._body)

        if role == "user":
            row.addStretch(1)
            row.addWidget(bubble)
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
            row.addWidget(bubble)
            row.addStretch(1)

        self.set_text(text)

    def append_token(self, token: str) -> None:
        self._text += token
        self._set_plain_text(self._text)
        self._sync_height()

    def set_text(self, text: str) -> None:
        self._text = text
        self._set_plain_text(text)
        self._sync_height()

    def render_markdown(self) -> None:
        if isinstance(self._body, QTextBrowser):
            self._body.setMarkdown(self._text)
        self._sync_height()

    def _set_plain_text(self, text: str) -> None:
        if isinstance(self._body, QTextBrowser):
            self._body.setPlainText(text)
        else:
            self._body.setText(text)

    def _sync_height(self) -> None:
        if not isinstance(self._body, QTextBrowser):
            self._body.adjustSize()
            return

        document = self._body.document()
        document.setTextWidth(self.BODY_MAX_WIDTH)
        width = min(self.BODY_MAX_WIDTH, max(24, int(document.idealWidth()) + 2))
        document.setTextWidth(width)
        height = max(22, int(document.size().height()) + 2)
        self._body.setFixedSize(QSize(width, height))
