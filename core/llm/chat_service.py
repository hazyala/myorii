from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
import re

from core.llm.attachments import AttachmentContext, AttachmentRouter
from core.llm.contracts import ChatAttachmentPayload, ChatMessagePayload, ChatRequest
from core.llm.ollama_client import ModelNotFound, OllamaClient, OllamaNotRunning, ContextLimitExceeded
from core.llm.router import IntentRouter, ModelRouter, PromptProfileResolver, ResponseFormatter


DEFAULT_MODEL = "qwen3-vl:4b-instruct"
MAX_ATTACHMENT_CONTEXT_CHARS = 3600
ATTACHMENT_CONTEXT_TRUNCATION_NOTICE = "\n[일부 생략: 내용이 많거나 복잡한 첨부파일은 일부 내용만 참고할 수 있습니다.]"
ATTACHMENT_CONTEXT_HEADER = "첨부파일 참고 내용:"


class EmptyModelResponse(RuntimeError):
    pass


class ChatService:
    def __init__(self, model: str = DEFAULT_MODEL, client: OllamaClient | None = None) -> None:
        self._provider = "ollama"
        self._model = model
        self._client = client or OllamaClient()
        self._intent_router = IntentRouter()
        self._model_router = ModelRouter()
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
        self._model_router = ModelRouter()

    def set_backend(self, provider: str, model: str) -> None:
        if provider not in ("ollama","openai","gemini","anthropic"):
            raise ValueError("Unknown provider")
        self._provider = provider
        self._model = model
        self._model_cache = None

    def invalidate_models(self) -> None:
        self._model_cache = None

    def warmup(self) -> None:
        if self._provider == "ollama": self._client.warmup(self._model)

    def available_models(self) -> list[str]:
        if self._provider != "ollama": return [self._model] if self._model else []
        try:
            models = self._list_models_cached()
        except OllamaNotRunning:
            return []
        return models

    def clear(self) -> None:
        self._messages.clear()

    @property
    def history(self) -> tuple[ChatMessagePayload, ...]:
        return tuple(self._messages)

    def restore_message(self, message: ChatMessagePayload, model_content: str | None = None) -> ChatMessagePayload:
        available = tuple(a for a in message.attachments if Path(a.path).is_file())
        missing = [a.name for a in message.attachments if a not in available]
        restored = replace(message, attachments=available)
        if model_content is not None:
            restored = replace(restored, content=model_content)
        elif available:
            try:
                restored = self._with_attachment_context(restored)
            except (RuntimeError, ValueError, OSError):
                restored = replace(restored, content=restored.content + "\n[이전 첨부 내용을 복원하지 못했습니다. 파일을 다시 첨부해주세요.]")
        if missing:
            restored = replace(restored, content=restored.content + "\n[이전 첨부 원본 없음: " + ", ".join(missing) + "]")
        return restored

    def set_history(self, messages: list[ChatMessagePayload]) -> None:
        self._messages = list(messages)

    def _request_history(self, intent: str, text: str, system_prompt: str) -> tuple[ChatMessagePayload, ...]:
        # Independent naming/translation tasks must not inherit unrelated answers.
        refers_back = bool(re.search(r"이전|앞서|방금|위의|그걸|그거|그것|같은|다시|더 |이걸|이거|이것|앞의|위 내용|위 문장|previous|above|that|same|again", text, re.I))
        if (intent.startswith("naming_") or intent == "translate") and not refers_back:
            return ()
        budget = max(0, 12000 - len(system_prompt) - len(text))
        selected: list[ChatMessagePayload] = []
        # Keep complete recent exchanges; never start history with an orphan assistant.
        for index in range(len(self._messages) - 2, -1, -2):
            pair = self._messages[index:index + 2]
            cost = sum(len(m.content) + 64 + (2000 if any(a.is_image for a in m.attachments) else 0) for m in pair)
            if len(selected) >= 12 or cost > budget:
                break
            selected[0:0] = pair
            budget -= cost
        return tuple(selected)

    def send(
        self,
        user_text: str,
        attachments: tuple[ChatAttachmentPayload, ...] = (),
    ) -> Iterator[str]:
        provider = self._provider
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

        route = self._intent_router.route(request)
        # Follow-up attachment questions retain the attachment profile, even when
        # a negated word such as "수정 코드는 필요 없어" triggers a code rule.
        if not attachments and re.search(r"첨부|방금|이전|그 파일|그 이미지|위 문서", text):
            previous = next((m for m in reversed(request.history) if m.role == "user" and m.attachments), None)
            if previous is not None and route.intent in {"simple_chat", "code_explain", "code_fix"}:
                route = self._intent_router.route(replace(request, user_message=replace(user_message, attachments=previous.attachments)))
        system_prompt = self._prompt_profile_resolver.resolve(route.intent)
        if len(system_prompt) + len(user_message.content) > 12000:
            raise ContextLimitExceeded("입력 내용이 너무 길어요. 내용을 나누어 보내주세요.")
        request = replace(request, history=self._request_history(route.intent, text, system_prompt))
        models = self._list_models_cached() if provider == "ollama" else [self._model]
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
        if provider == "ollama":
            stream = self._client.stream_chat(request.model, request.messages())
        else:
            from core.llm.cloud_client import CloudClient
            stream = CloudClient(provider).stream_chat(request.model, request.messages())
        if self._response_formatter.should_buffer(route.intent):
            assistant_text = "".join(stream)
            assistant_text = self._response_formatter.format(assistant_text, route.intent, request)
            if assistant_text:
                yield assistant_text
        else:
            for token in stream:
                assistant_text += token
                yield token

        if not assistant_text.strip():
            raise EmptyModelResponse("모델 응답이 비어 있습니다. 같은 요청을 다시 보내거나 새 대화에서 다시 시도해주세요.")

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

        self._model_cache = self._client.list_models()
        return self._model_cache
