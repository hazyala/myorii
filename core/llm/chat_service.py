from __future__ import annotations

from collections.abc import Iterator

from core.llm.contracts import ChatAttachmentPayload, ChatMessagePayload, ChatRequest
from core.llm.ollama_client import ModelNotFound, OllamaClient, OllamaNotRunning
from core.llm.prompt_loader import load_prompt
from core.llm.router import InstantRouter, IntentRouter


DEFAULT_MODEL = "qwen3-vl:4b"


class ChatService:
    def __init__(self, model: str = DEFAULT_MODEL, client: OllamaClient | None = None) -> None:
        self._model = model
        self._client = client or OllamaClient()
        self._instant_router = InstantRouter()
        self._intent_router = IntentRouter()
        self._messages: list[ChatMessagePayload] = []

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

    def send(
        self,
        user_text: str,
        attachments: tuple[ChatAttachmentPayload, ...] = (),
    ) -> Iterator[str]:
        text = user_text.strip()
        if not text and not attachments:
            return

        user_message = ChatMessagePayload(role="user", content=text, attachments=attachments)
        request = ChatRequest(
            model=self._model,
            system_prompt=load_prompt(),
            history=tuple(self._messages),
            user_message=user_message,
        )

        instant_response = self._instant_router.match(request)
        if instant_response is not None:
            self._messages.append(user_message)
            self._messages.append(
                ChatMessagePayload(
                    role="assistant",
                    content=instant_response.content,
                    metadata={"intent": instant_response.intent, "route": "instant"},
                )
            )
            yield instant_response.content
            return

        route = self._intent_router.route(request)
        models = self._client.list_models()
        if self._model not in models:
            raise ModelNotFound(f"모델이 설치돼 있지 않아요: {self._model}")

        assistant_text = ""

        for token in self._client.stream_chat(request.model, request.messages()):
            assistant_text += token
            yield token

        self._messages.append(user_message)
        self._messages.append(
            ChatMessagePayload(
                role="assistant",
                content=assistant_text,
                metadata={"intent": route.intent, "route_reason": route.reason},
            )
        )
