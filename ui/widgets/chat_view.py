from __future__ import annotations

from PyQt6.QtCore import QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QKeyEvent, QTextOption
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.llm.chat_service import ChatService
from ui.assets import asset_path
from ui.chat_worker import ChatWorker
from ui.widgets.message_bubble import MessageBubble
from ui.widgets.switch_button import SwitchButton


class ChatInput(QTextEdit):
    send_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("promptInput")
        self.setPlaceholderText("무엇을 도와줄까?")
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(2)
        self.setFixedHeight(32)
        self.textChanged.connect(self._fit_height_to_document)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                return

            self._request_send()
            return

        super().keyPressEvent(event)

    def request_send(self) -> None:
        self._request_send()

    def _request_send(self) -> None:
        text = self.toPlainText().strip()
        if not text:
            return

        self.send_requested.emit(text)
        self.clear()

    def _fit_height_to_document(self) -> None:
        line_count = max(1, self.toPlainText().count("\n") + 1)
        next_height = 32 + ((line_count - 1) * 18)
        self.setFixedHeight(min(next_height, 78))


class ChatView(QWidget):
    def __init__(self, chat_service: ChatService | None = None) -> None:
        super().__init__()
        self.setObjectName("chatView")
        self._chat_service = chat_service or ChatService()
        self._worker = ChatWorker(self._chat_service)
        self._assistant_bubble: MessageBubble | None = None
        self._history_enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._chat_scroll_area(), 1)
        layout.addWidget(self._input_panel())

        self._worker.token.connect(self._append_assistant_token)
        self._worker.finished.connect(self._finish_response)
        self._worker.error.connect(self._show_error)

    def set_model(self, model: str) -> None:
        self._chat_service.set_model(model)

    def _chat_scroll_area(self) -> QWidget:
        self._scroll_area = QScrollArea()
        self._scroll_area.setObjectName("chatScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("chatScrollContent")
        self._message_layout = QVBoxLayout(content)
        self._message_layout.setContentsMargins(0, 0, 0, 0)
        self._message_layout.setSpacing(10)
        self._message_layout.addStretch(1)

        self._scroll_area.setWidget(content)
        return self._scroll_area

    def _input_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("inputPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        input_actions = QHBoxLayout()
        input_actions.setSpacing(7)

        attachment_button = QPushButton("+")
        attachment_button.setObjectName("attachmentButton")
        attachment_button.setFixedSize(22, 22)
        attachment_button.setCursor(Qt.CursorShape.PointingHandCursor)
        attachment_button.setEnabled(False)

        attachment_label = QLabel("첨부파일")
        attachment_label.setObjectName("attachmentLabel")

        history_label = QLabel("대화 기록 저장")
        history_label.setObjectName("historyLabel")
        self._history_switch = SwitchButton()
        self._history_switch.setObjectName("historySwitch")
        self._history_switch.toggled.connect(self._set_history_enabled)

        input_actions.addWidget(attachment_button)
        input_actions.addWidget(attachment_label)
        input_actions.addStretch(1)
        input_actions.addWidget(history_label)
        input_actions.addWidget(self._history_switch)

        prompt_wrap = QFrame()
        prompt_wrap.setObjectName("promptWrap")
        prompt_layout = QHBoxLayout(prompt_wrap)
        prompt_layout.setContentsMargins(13, 7, 8, 7)
        prompt_layout.setSpacing(7)

        self._prompt = ChatInput()
        self._send_button = QPushButton()
        self._send_button.setObjectName("sendButton")
        self._send_button.setIcon(QIcon(str(asset_path("icons", "send.png"))))
        self._send_button.setIconSize(QSize(19, 19))
        self._send_button.setFixedSize(38, 38)
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.clicked.connect(self._prompt.request_send)
        self._prompt.send_requested.connect(self._send_message)

        prompt_layout.addWidget(self._prompt, 1, Qt.AlignmentFlag.AlignVCenter)
        prompt_layout.addWidget(self._send_button, 0, Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(input_actions)
        layout.addWidget(prompt_wrap)

        return frame

    def _send_message(self, text: str) -> None:
        if self._worker.is_running:
            return

        self._add_message("user", text)
        self._assistant_bubble = self._add_message("assistant", "")
        self._set_input_enabled(False)
        self._worker.start(text)
        self._scroll_to_bottom()

    def _add_message(self, role: str, text: str) -> MessageBubble:
        bubble = MessageBubble(role, text)
        insert_index = max(0, self._message_layout.count() - 1)
        self._message_layout.insertWidget(insert_index, bubble)
        self._scroll_to_bottom()
        return bubble

    def _append_assistant_token(self, token: str) -> None:
        if self._assistant_bubble is None:
            return

        self._assistant_bubble.append_token(token)
        self._scroll_to_bottom()

    def _finish_response(self) -> None:
        if self._assistant_bubble is not None:
            self._assistant_bubble.render_markdown()
        self._assistant_bubble = None
        self._set_input_enabled(True)
        self._scroll_to_bottom()

    def _show_error(self, message: str) -> None:
        if self._assistant_bubble is not None:
            self._assistant_bubble.set_text(message)
            self._assistant_bubble.render_markdown()
            self._assistant_bubble = None
        else:
            self._add_message("assistant", message)
        self._set_input_enabled(True)
        self._scroll_to_bottom()

    def _set_input_enabled(self, enabled: bool) -> None:
        self._prompt.setEnabled(enabled)
        self._send_button.setEnabled(enabled)
        if enabled:
            self._prompt.setFocus()

    def _set_history_enabled(self, enabled: bool) -> None:
        self._history_enabled = enabled

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))
