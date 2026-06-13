from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import ollama

from core.llm.attachments import ImageHandler
from core.llm.contracts import ChatMessagePayload


class OllamaError(RuntimeError):
    pass


class OllamaNotRunning(OllamaError):
    pass


class ModelNotFound(OllamaError):
    pass


class ContextLimitExceeded(OllamaError):
    pass


class InvalidImageAttachment(OllamaError):
    pass


OLLAMA_NOT_RUNNING_MESSAGE = "Ollama가 실행 중이 아니에요. Ollama를 실행한 뒤 다시 시도해주세요."


class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        self._client = ollama.Client(host=host) if host else ollama.Client()
        self._image_handler = ImageHandler()

    def is_available(self) -> bool:
        try:
            self._client.list()
        except Exception:
            return False
        return True

    def list_models(self) -> list[str]:
        try:
            response = self._client.list()
        except Exception as exc:
            raise OllamaNotRunning(OLLAMA_NOT_RUNNING_MESSAGE) from exc

        models = self._value(response, "models", [])
        names: list[str] = []
        for model in models:
            name = self._value(model, "model") or self._value(model, "name")
            if name:
                names.append(str(name))
        return names

    def warmup(self, model: str) -> None:
        try:
            self._client.chat(model=model, messages=[], stream=False, keep_alive="30m")
        except Exception as exc:
            raise OllamaNotRunning(OLLAMA_NOT_RUNNING_MESSAGE) from exc

    def stream_chat(self, model: str, messages: list[ChatMessagePayload]) -> Iterator[str]:
        ollama_messages = self._to_ollama_messages(messages)

        try:
            stream = self._client.chat(
                model=model,
                messages=ollama_messages,
                stream=True,
                keep_alive="30m",
            )
            for chunk in stream:
                content = self._value(self._value(chunk, "message", {}), "content", "")
                if content:
                    yield str(content)
        except ollama.ResponseError as exc:
            if exc.status_code == 404 or "not found" in str(exc).lower():
                raise ModelNotFound(f"모델이 설치돼 있지 않아요: {model}") from exc
            message = str(exc)
            if self._is_context_limit_error(message):
                raise ContextLimitExceeded(self._context_limit_message(messages)) from exc
            if self._is_invalid_image_error(message):
                raise InvalidImageAttachment(
                    "이미지 파일을 읽을 수 없습니다. 파일이 손상되었거나 지원하지 않는 이미지일 수 있습니다."
                ) from exc
            raise OllamaError(str(exc)) from exc
        except Exception as exc:
            raise OllamaNotRunning(OLLAMA_NOT_RUNNING_MESSAGE) from exc

    @staticmethod
    def _value(data: Any, key: str, default: Any = None) -> Any:
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    def _to_ollama_messages(self, messages: list[ChatMessagePayload]) -> list[dict[str, Any]]:
        ollama_messages: list[dict[str, Any]] = []
        for message in messages:
            ollama_message: dict[str, Any] = {
                "role": message.role,
                "content": message.content,
            }
            images = [
                self._image_handler.to_base64(attachment)
                for attachment in message.attachments
                if attachment.is_image
            ]
            if images:
                ollama_message["images"] = images
            ollama_messages.append(ollama_message)
        return ollama_messages

    @staticmethod
    def _context_limit_message(messages: list[ChatMessagePayload]) -> str:
        if OllamaClient._last_user_message_has_attachments(messages):
            return "첨부파일 용량이 커서 응답 용량이 초과되었습니다. 첨부파일을 줄이거나 새 대화에서 다시 시도해주세요."
        return "대화가 길어져 응답 용량이 초과되었습니다. 새로운 대화를 시작해주세요."

    @staticmethod
    def _last_user_message_has_attachments(messages: list[ChatMessagePayload]) -> bool:
        for message in reversed(messages):
            if message.role == "user":
                return bool(message.attachments)
        return False

    @staticmethod
    def _is_context_limit_error(message: str) -> bool:
        normalized = message.lower()
        return (
            "exceeds the available context size" in normalized
            or "context length" in normalized
            or "context size" in normalized
            or "num_ctx" in normalized
        )

    @staticmethod
    def _is_invalid_image_error(message: str) -> bool:
        normalized = message.lower()
        return (
            "failed to load image or audio file" in normalized
            or "invalid image" in normalized
            or "unsupported image" in normalized
            or ("image" in normalized and "decode" in normalized)
        )
