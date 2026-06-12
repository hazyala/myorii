from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QEvent, QMimeData, QPropertyAnimation, QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QFontMetrics,
    QIcon,
    QKeyEvent,
    QPainter,
    QPen,
    QPixmap,
    QTextOption,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.llm.chat_service import ChatService
from core.llm.contracts import ChatAttachmentPayload
from ui.assets import asset_path
from ui.chat_worker import ChatWorker
from ui.widgets.message_bubble import MessageAttachment, MessageBubble
from ui.widgets.switch_button import SwitchButton


SUPPORTED_ATTACHMENT_EXTENSIONS = {
    ".bmp",
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".hwp",
    ".hwpx",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".py",
    ".rtf",
    ".tsv",
    ".txt",
    ".xls",
    ".xlsx",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class ChatAttachment:
    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()

    @property
    def is_image(self) -> bool:
        return self.suffix in {".bmp", ".gif", ".jpeg", ".jpg", ".png"}


class ElidedLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__()
        self._full_text = text
        self.setText(text)

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self._sync_text()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_text()

    def _sync_text(self) -> None:
        metrics = QFontMetrics(self.font())
        self.setText(metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width()))


class AttachmentPreview(QFrame):
    removed = pyqtSignal(Path)

    def __init__(self, attachment: ChatAttachment) -> None:
        super().__init__()
        self._attachment = attachment
        self.setObjectName("attachmentPreview")
        self.setFixedHeight(42)
        self.setMinimumWidth(128)
        self.setMaximumWidth(188)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 7, 6)
        layout.setSpacing(7)

        thumbnail = QLabel()
        thumbnail.setObjectName("attachmentThumbnail")
        thumbnail.setFixedSize(30, 30)
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if attachment.is_image:
            pixmap = QPixmap(str(attachment.path))
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

        name = ElidedLabel(attachment.name)
        name.setObjectName("attachmentName")
        name.setToolTip(str(attachment.path))

        remove_button = QPushButton("×")
        remove_button.setObjectName("attachmentRemoveButton")
        remove_button.setFixedSize(20, 20)
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.clicked.connect(lambda: self.removed.emit(self._attachment.path))

        layout.addWidget(thumbnail)
        layout.addWidget(name, 1)
        layout.addWidget(remove_button)


class ChatInput(QTextEdit):
    send_requested = pyqtSignal(str)
    files_dropped = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("promptInput")
        self.setPlaceholderText("무엇을 도와줄까?")
        self.setAcceptRichText(False)
        self.setAcceptDrops(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(2)
        self.setFixedHeight(32)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)
        self.textChanged.connect(self._fit_height_to_document)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                return

            self._request_send()
            return

        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._has_local_files(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        if self._has_local_files(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        files = self._local_files_from_event(event)
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if watched is self.viewport():
            if isinstance(event, QDropEvent):
                files = self._local_files_from_event(event)
                if files:
                    self.files_dropped.emit(files)
                    event.acceptProposedAction()
                    return True
            if isinstance(event, (QDragEnterEvent, QDragMoveEvent)) and self._has_local_files(event):
                event.acceptProposedAction()
                return True

        return super().eventFilter(watched, event)

    def insertFromMimeData(self, source: QMimeData) -> None:  # noqa: N802
        files = self._local_files_from_mime_data(source)
        if files:
            self.files_dropped.emit(files)
            return
        super().insertFromMimeData(source)

    def request_send(self) -> None:
        self._request_send()

    def _request_send(self) -> None:
        text = self.toPlainText().strip()
        self.send_requested.emit(text)

    def _fit_height_to_document(self) -> None:
        line_count = max(1, self.toPlainText().count("\n") + 1)
        next_height = 32 + ((line_count - 1) * 18)
        self.setFixedHeight(min(next_height, 78))

    def _has_local_files(self, event: QDragEnterEvent | QDragMoveEvent | QDropEvent) -> bool:
        return bool(self._local_files_from_event(event))

    def _local_files_from_event(self, event: QDragEnterEvent | QDragMoveEvent | QDropEvent) -> list[str]:
        return self._local_files_from_mime_data(event.mimeData())

    def _local_files_from_mime_data(self, mime_data: QMimeData) -> list[str]:
        if not mime_data.hasUrls():
            return []
        return [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]


class ChatView(QWidget):
    def __init__(self, chat_service: ChatService | None = None) -> None:
        super().__init__()
        self.setObjectName("chatView")
        self.setAcceptDrops(True)
        self._chat_service = chat_service or ChatService()
        self._worker = ChatWorker(self._chat_service)
        self._assistant_bubble: MessageBubble | None = None
        self._attachments: list[ChatAttachment] = []
        self._history_enabled = False
        self._toast = QLabel("복사됨", self)
        self._toast.setObjectName("copyToast")
        self._toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast.hide()
        self._toast_opacity = QGraphicsOpacityEffect(self._toast)
        self._toast.setGraphicsEffect(self._toast_opacity)
        self._toast_animation = QPropertyAnimation(self._toast_opacity, b"opacity", self)
        self._toast_animation.setDuration(1200)
        self._toast_animation.setStartValue(1.0)
        self._toast_animation.setEndValue(0.0)
        self._toast_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._toast_animation.finished.connect(self._toast.hide)

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
        layout.setContentsMargins(10, 8, 10, 0)
        layout.setSpacing(4)

        input_actions = QHBoxLayout()
        input_actions.setSpacing(7)

        history_list = QPushButton("채팅 기록")
        history_list.setObjectName("historyListButton")
        history_list.setIcon(self._list_icon())
        history_list.setIconSize(QSize(15, 15))
        history_list.setFixedHeight(28)
        history_list.setCursor(Qt.CursorShape.PointingHandCursor)

        history_label = QLabel("대화 기록 저장")
        history_label.setObjectName("historyLabel")
        self._history_switch = SwitchButton()
        self._history_switch.setObjectName("historySwitch")
        self._history_switch.toggled.connect(self._set_history_enabled)

        input_actions.addWidget(history_list)
        input_actions.addStretch(1)
        input_actions.addWidget(history_label)
        input_actions.addWidget(self._history_switch)

        prompt_wrap = QFrame()
        prompt_wrap.setObjectName("promptWrap")
        prompt_layout = QHBoxLayout(prompt_wrap)
        prompt_layout.setContentsMargins(13, 3, 8, 3)
        prompt_layout.setSpacing(7)

        self._plus_button = QPushButton("+")
        self._plus_button.setObjectName("promptPlusButton")
        self._plus_button.setFixedSize(38, 38)
        self._plus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus_button.clicked.connect(self._select_attachments)
        self._prompt = ChatInput()
        self._send_button = QPushButton()
        self._send_button.setObjectName("sendButton")
        self._send_button.setIcon(QIcon(str(asset_path("icons", "send.png"))))
        self._send_button.setIconSize(QSize(19, 19))
        self._send_button.setFixedSize(38, 38)
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.clicked.connect(self._prompt.request_send)
        self._prompt.send_requested.connect(self._send_message)
        self._prompt.files_dropped.connect(self._add_attachment_paths)

        prompt_layout.addWidget(self._plus_button, 0, Qt.AlignmentFlag.AlignBottom)
        prompt_layout.addWidget(self._prompt, 1, Qt.AlignmentFlag.AlignVCenter)
        prompt_layout.addWidget(self._send_button, 0, Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(input_actions)
        self._attachment_row = QScrollArea()
        self._attachment_row.setObjectName("attachmentPreviewArea")
        self._attachment_row.setWidgetResizable(True)
        self._attachment_row.setFrameShape(QFrame.Shape.NoFrame)
        self._attachment_row.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._attachment_row.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._attachment_row.setFixedHeight(0)
        self._attachment_row.hide()

        self._attachment_content = QWidget()
        self._attachment_content.setObjectName("attachmentPreviewContent")
        self._attachment_layout = QHBoxLayout(self._attachment_content)
        self._attachment_layout.setContentsMargins(0, 0, 0, 0)
        self._attachment_layout.setSpacing(6)
        self._attachment_layout.addStretch(1)
        self._attachment_row.setWidget(self._attachment_content)

        layout.addWidget(self._attachment_row)
        layout.addWidget(prompt_wrap)

        return frame

    def _list_icon(self) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#565f6e"), 1.7))
        for y in (4, 8, 12):
            painter.drawPoint(3, y)
            painter.drawLine(6, y, 13, y)
        painter.end()
        return QIcon(pixmap)

    def _send_message(self, text: str) -> None:
        if self._worker.is_running:
            return
        if not text and not self._attachments:
            return

        request_text = self._message_text_with_attachments(text)
        message_attachments = self._message_attachments()
        request_attachments = self._request_attachments()
        self._add_message("user", text, message_attachments)
        self._prompt.clear()
        self._clear_attachments()
        self._assistant_bubble = self._add_message("assistant", "")
        self._assistant_bubble.show_loading_indicator()
        self._set_input_enabled(False)
        self._worker.start(request_text, request_attachments)
        self._scroll_to_bottom()

    def _add_message(
        self,
        role: str,
        text: str,
        attachments: list[MessageAttachment] | None = None,
    ) -> MessageBubble:
        bubble = MessageBubble(role, text, attachments)
        bubble.update_available_width(self._available_message_width())
        bubble.code_copied.connect(self._show_copy_toast)
        insert_index = max(0, self._message_layout.count() - 1)
        self._message_layout.insertWidget(insert_index, bubble)
        self._scroll_to_bottom()
        return bubble

    def _append_assistant_token(self, token: str) -> None:
        if self._assistant_bubble is None:
            return

        self._assistant_bubble.hide_loading_indicator()
        self._assistant_bubble.append_token(token)
        self._scroll_to_bottom()

    def _finish_response(self) -> None:
        if self._assistant_bubble is not None:
            self._assistant_bubble.hide_loading_indicator()
            self._assistant_bubble.render_markdown()
        self._assistant_bubble = None
        self._set_input_enabled(True)
        self._scroll_to_bottom()

    def _show_error(self, message: str) -> None:
        if self._assistant_bubble is not None:
            self._assistant_bubble.hide_loading_indicator()
            self._assistant_bubble.set_text(message)
            self._assistant_bubble.render_markdown()
            self._assistant_bubble = None
        else:
            self._add_message("assistant", message)
        self._set_input_enabled(True)
        self._scroll_to_bottom()

    def _set_input_enabled(self, enabled: bool) -> None:
        self._prompt.setEnabled(enabled)
        self._plus_button.setEnabled(enabled)
        self._send_button.setEnabled(enabled)
        if enabled:
            self._prompt.setFocus()

    def _set_history_enabled(self, enabled: bool) -> None:
        self._history_enabled = enabled

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def _available_message_width(self) -> int:
        viewport_width = self._scroll_area.viewport().width()
        own_width = self.width()
        if own_width > 0:
            viewport_width = min(viewport_width, own_width)
        return max(0, viewport_width)

    def _show_copy_toast(self, _code: str) -> None:
        self._toast.adjustSize()
        self._toast.setFixedWidth(max(64, self._toast.width() + 18))
        self._position_toast()
        self._toast_opacity.setOpacity(1.0)
        self._toast.show()
        self._toast.raise_()
        self._toast_animation.stop()
        self._toast_animation.start()

    def _position_toast(self) -> None:
        self._toast.move(
            (self.width() - self._toast.width()) // 2,
            max(12, self.height() - self._toast.height() - 86),
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        width = self._available_message_width()
        for index in range(self._message_layout.count()):
            widget = self._message_layout.itemAt(index).widget()
            if isinstance(widget, MessageBubble):
                widget.update_available_width(width)
        self._position_toast()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._has_local_files(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        if self._has_local_files(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        files = self._local_files_from_event(event)
        if files:
            self._add_attachment_paths(files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _select_attachments(self) -> None:
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "파일 첨부",
            str(Path.home()),
            "지원 파일 (*.jpg *.jpeg *.png *.txt *.md *.csv *.tsv *.json *.yaml *.yml *.pdf *.doc *.docx *.hwp *.hwpx *.xls *.xlsx *.ppt *.pptx);;모든 파일 (*)",
        )
        self._add_attachment_paths(paths)

    def _add_attachment_paths(self, paths: list[str]) -> None:
        if self._worker.is_running:
            return

        unsupported: list[str] = []
        existing = {attachment.path for attachment in self._attachments}
        for value in paths:
            path = Path(value)
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_ATTACHMENT_EXTENSIONS:
                unsupported.append(path.name or str(path))
                continue
            if path in existing:
                continue
            self._attachments.append(ChatAttachment(path))
            existing.add(path)

        self._refresh_attachment_previews()
        if unsupported:
            names = ", ".join(unsupported)
            self._show_error(f"지원하지 않는 파일 형식입니다: {names}")

    def _refresh_attachment_previews(self) -> None:
        while self._attachment_layout.count() > 1:
            item = self._attachment_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for attachment in self._attachments:
            preview = AttachmentPreview(attachment)
            preview.removed.connect(self._remove_attachment)
            self._attachment_layout.insertWidget(self._attachment_layout.count() - 1, preview)

        has_attachments = bool(self._attachments)
        self._attachment_row.setVisible(has_attachments)
        self._attachment_row.setFixedHeight(48 if has_attachments else 0)

    def _remove_attachment(self, path: Path) -> None:
        self._attachments = [attachment for attachment in self._attachments if attachment.path != path]
        self._refresh_attachment_previews()

    def _clear_attachments(self) -> None:
        self._attachments.clear()
        self._refresh_attachment_previews()

    def _message_text_with_attachments(self, text: str) -> str:
        if not self._attachments:
            return text
        names = "\n".join(f"- {attachment.name}" for attachment in self._attachments)
        if not text:
            return f"첨부 파일:\n{names}"
        return f"{text}\n\n첨부 파일:\n{names}"

    def _message_attachments(self) -> list[MessageAttachment]:
        return [
            MessageAttachment(
                path=str(attachment.path),
                name=attachment.name,
                suffix=attachment.suffix,
                is_image=attachment.is_image,
            )
            for attachment in self._attachments
        ]

    def _request_attachments(self) -> tuple[ChatAttachmentPayload, ...]:
        return tuple(
            ChatAttachmentPayload.from_path(attachment.path)
            for attachment in self._attachments
            if attachment.is_image
        )

    def _has_local_files(self, event: QDragEnterEvent | QDragMoveEvent | QDropEvent) -> bool:
        return bool(self._local_files_from_event(event))

    def _local_files_from_event(self, event: QDragEnterEvent | QDragMoveEvent | QDropEvent) -> list[str]:
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return []
        return [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]
