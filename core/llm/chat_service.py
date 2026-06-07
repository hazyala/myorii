from __future__ import annotations

from collections.abc import Iterator

from core.llm.ollama_client import ModelNotFound, OllamaClient, OllamaNotRunning
from core.llm.prompt_loader import load_prompt


DEFAULT_MODEL = "qwen3-vl:4b"


class ChatService:
    def __init__(self, model: str = DEFAULT_MODEL, client: OllamaClient | None = None) -> None:
        self._model = model
        self._client = client or OllamaClient()
        self._messages: list[dict[str, str]] = []

    @property
    def model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        self._model = model or DEFAULT_MODEL

    def available_models(self) -> list[str]:
        try:
            models = self._client.list_models()
        except OllamaNotRunning:
            models = []

        return [DEFAULT_MODEL, *(model for model in models if model != DEFAULT_MODEL)]

    def clear(self) -> None:
        self._messages.clear()

    def send(self, user_text: str) -> Iterator[str]:
        text = user_text.strip()
        if not text:
            return

        if not self._client.is_available():
            raise OllamaNotRunning("Ollama가 실행 중이 아니에요")

        if self._model not in self._client.list_models():
            raise ModelNotFound(f"모델이 설치돼 있지 않아요: {self._model}")

        request_messages = [
            {"role": "system", "content": load_prompt()},
            *self._messages,
            {"role": "user", "content": text},
        ]
        assistant_text = ""

        for token in self._client.stream_chat(self._model, request_messages):
            assistant_text += token
            yield token

        self._messages.append({"role": "user", "content": text})
        self._messages.append({"role": "assistant", "content": assistant_text})
