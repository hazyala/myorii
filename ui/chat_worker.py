from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, pyqtSignal

from core.llm.chat_service import ChatService
from core.llm.contracts import ChatAttachmentPayload


class ChatWorker(QObject):
    token = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, chat_service: ChatService) -> None:
        super().__init__()
        self._chat_service = chat_service
        self._stop_requested = False
        self._thread: threading.Thread | None = None

    def start(self, text: str, attachments: tuple[ChatAttachmentPayload, ...] = ()) -> None:
        if self.is_running:
            return

        self._stop_requested = False
        self._thread = threading.Thread(target=self._run, args=(text, attachments), daemon=True)
        self._thread.start()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def stop(self) -> None:
        self._stop_requested = True

    def _run(self, text: str, attachments: tuple[ChatAttachmentPayload, ...]) -> None:
        try:
            generated_text = ""
            for token in self._chat_service.send(text, attachments):
                if self._stop_requested:
                    break
                generated_text += token
                self.token.emit(token)
            self.finished.emit(generated_text)
        except Exception as exc:
            self.error.emit(str(exc))


class ModelListWorker(QObject):
    models_loaded = pyqtSignal(list)

    def __init__(self, chat_service: ChatService) -> None:
        super().__init__()
        self._chat_service = chat_service
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.is_running:
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        self.models_loaded.emit(self._chat_service.available_models())
