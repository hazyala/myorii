from __future__ import annotations

import os
from dataclasses import dataclass

from core.llm.contracts import ChatRequest


FAST_TEXT_MODEL = "qwen3:1.7b"


@dataclass(frozen=True)
class ModelRoute:
    model: str
    reason: str


class ModelRouter:
    """Chooses the lightest installed model that can handle the request."""

    def __init__(
        self,
        fast_text_model: str | None = None,
        vision_model: str | None = None,
    ) -> None:
        self._fast_text_model = fast_text_model or os.getenv("MYORII_FAST_TEXT_MODEL", FAST_TEXT_MODEL)
        self._vision_model = vision_model or os.getenv("MYORII_VISION_MODEL")

    def route(
        self,
        request: ChatRequest,
        intent: str,
        available_models: tuple[str, ...],
    ) -> ModelRoute:
        installed = set(available_models)
        selected_model = request.model
        vision_model = self._vision_model or selected_model

        if self._needs_vision(request, intent):
            if vision_model in installed:
                return ModelRoute(model=vision_model, reason="vision_intent")
            return ModelRoute(model=selected_model, reason="vision_fallback_selected")

        if self._fast_text_model in installed:
            return ModelRoute(model=self._fast_text_model, reason="fast_text")

        return ModelRoute(model=selected_model, reason="fast_text_fallback_selected")

    @staticmethod
    def _needs_vision(request: ChatRequest, intent: str) -> bool:
        if intent in {"image_question", "image_code_transcription"}:
            return True
        return any(attachment.is_image for attachment in request.user_message.attachments)
