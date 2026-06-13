from __future__ import annotations

from collections.abc import Iterator

from core.llm.attachments import AttachmentContext, AttachmentRouter
from core.llm.contracts import ChatAttachmentPayload, ChatMessagePayload, ChatRequest
from core.llm.ollama_client import ModelNotFound, OllamaClient, OllamaNotRunning
from core.llm.router import InstantRouter, IntentRouter, ModelRouter, PromptProfileResolver, ResponseFormatter


DEFAULT_MODEL = "qwen3-vl:4b"
MAX_ATTACHMENT_CONTEXT_CHARS = 3600
ATTACHMENT_CONTEXT_TRUNCATION_NOTICE = "\n[일부 생략: 내용이 많거나 복잡한 첨부파일은 일부 내용만 참고할 수 있습니다.]"
ATTACHMENT_CONTEXT_HEADER = "첨부파일 참고 내용:"


class ChatService:
    def __init__(self, model: str = DEFAULT_MODEL, client: OllamaClient | None = None) -> None:
        self._model = model
        self._client = client or OllamaClient()
        self._instant_router = InstantRouter()
        self._intent_router = IntentRouter()
        self._model_router = ModelRouter(vision_model=self._model)
        self._prompt_profile_resolver = PromptProfileResolver()
        self._response_formatter = ResponseFormatter()
        self._attachment_router = AttachmentRouter()
        self._model_cache: list[str] | None = None
        self._messages: list[ChatMessagePayload] = []

    @property
    def model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        self._model = model or DEFAULT_MODEL
        self._model_router = ModelRouter(vision_model=self._model)

    def available_models(self) -> list[str]:
        models = self._list_models_cached()
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
        user_message = self._with_attachment_context(user_message)
        request = ChatRequest(
            model=self._model,
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
        system_prompt = self._prompt_profile_resolver.resolve(route.intent)
        models = self._list_models_cached()
        model_route = self._model_router.route(request, route.intent, tuple(models))
        if model_route.model not in models:
            raise ModelNotFound(f"모델이 설치돼 있지 않아요: {model_route.model}")

        request = ChatRequest(
            model=model_route.model,
            system_prompt=system_prompt,
            history=request.history,
            user_message=request.user_message,
            session_id=request.session_id,
            request_id=request.request_id,
            device=request.device,
            created_at=request.created_at,
            metadata={
                **request.metadata,
                "intent": route.intent,
                "route_reason": route.reason,
                "model_route_reason": model_route.reason,
            },
        )

        assistant_text = ""
        stream = self._client.stream_chat(request.model, request.messages())
        if self._response_formatter.should_buffer(route.intent):
            assistant_text = "".join(stream)
            assistant_text = self._response_formatter.format(assistant_text, route.intent, request)
            if assistant_text:
                yield assistant_text
        else:
            for token in stream:
                assistant_text += token
                yield token

        self._messages.append(user_message)
        self._messages.append(
            ChatMessagePayload(
                role="assistant",
                content=assistant_text,
                metadata={
                    "intent": route.intent,
                    "route_reason": route.reason,
                    "model": model_route.model,
                    "model_route_reason": model_route.reason,
                },
            )
        )

    def _with_attachment_context(self, message: ChatMessagePayload) -> ChatMessagePayload:
        contexts = self._attachment_router.build_contexts(message.attachments)
        if not contexts:
            return message

        context_text = self._format_attachment_contexts(contexts)
        content = f"{message.content}\n\n{context_text}" if message.content else context_text
        return ChatMessagePayload(
            role=message.role,
            content=content,
            attachments=message.attachments,
            sync=message.sync,
            created_at=message.created_at,
            metadata={
                **message.metadata,
                "attachment_contexts": [
                    {
                        "title": context.title,
                        "limitations": list(context.limitations),
                        "warnings": list(context.warnings),
                        "metadata": context.metadata,
                    }
                    for context in contexts
                ],
            },
        )

    @staticmethod
    def _format_attachment_contexts(contexts: tuple[AttachmentContext, ...]) -> str:
        if not contexts:
            return ATTACHMENT_CONTEXT_HEADER

        separator_chars = max(0, len(contexts) - 1) * 2
        available = max(0, MAX_ATTACHMENT_CONTEXT_CHARS - len(ATTACHMENT_CONTEXT_HEADER) - 1 - separator_chars)
        section_budget = max(1, available // len(contexts))
        sections = "\n\n".join(
            ChatService._truncate_attachment_section(context.to_prompt_section(), section_budget)
            for context in contexts
        )
        return f"{ATTACHMENT_CONTEXT_HEADER}\n{sections}"

    @staticmethod
    def _truncate_attachment_section(section: str, limit: int) -> str:
        if len(section) <= limit:
            return section
        notice = ATTACHMENT_CONTEXT_TRUNCATION_NOTICE
        if limit <= len(notice):
            return section[:limit].rstrip()
        return section[: limit - len(notice)].rstrip() + notice

    def _list_models_cached(self) -> list[str]:
        if self._model_cache is not None:
            return self._model_cache

        try:
            self._model_cache = self._client.list_models()
        except OllamaNotRunning:
            return []
        return self._model_cache
