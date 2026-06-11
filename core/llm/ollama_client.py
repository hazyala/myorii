from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ollama

from core.llm.contracts import ChatMessagePayload


class OllamaError(RuntimeError):
    pass


class OllamaNotRunning(OllamaError):
    pass


class ModelNotFound(OllamaError):
    pass


class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        self._client = ollama.Client(host=host) if host else ollama.Client()

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
            raise OllamaNotRunning("Ollama가 실행 중이 아니에요") from exc

        models = self._value(response, "models", [])
        names: list[str] = []
        for model in models:
            name = self._value(model, "model") or self._value(model, "name")
            if name:
                names.append(str(name))
        return names

    def stream_chat(self, model: str, messages: list[ChatMessagePayload]) -> Iterator[str]:
        ollama_messages = self._to_ollama_messages(messages)

        try:
            stream = self._client.chat(model=model, messages=ollama_messages, stream=True)
            for chunk in stream:
                content = self._value(self._value(chunk, "message", {}), "content", "")
                if content:
                    yield str(content)
        except ollama.ResponseError as exc:
            if exc.status_code == 404 or "not found" in str(exc).lower():
                raise ModelNotFound(f"모델이 설치돼 있지 않아요: {model}") from exc
            raise OllamaError(str(exc)) from exc
        except Exception as exc:
            raise OllamaNotRunning("Ollama가 실행 중이 아니에요") from exc

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
                self._image_to_base64(Path(attachment.path))
                for attachment in message.attachments
                if attachment.is_image
            ]
            if images:
                ollama_message["images"] = images
            ollama_messages.append(ollama_message)
        return ollama_messages

    def _image_to_base64(self, path: Path) -> str:
        try:
            return base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError as exc:
            raise OllamaError(f"이미지 파일을 읽을 수 없어요: {path.name}") from exc
