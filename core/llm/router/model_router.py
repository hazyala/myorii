from __future__ import annotations

from dataclasses import dataclass

from core.llm.contracts import ChatRequest


@dataclass(frozen=True)
class ModelRoute:
    model: str
    reason: str


class ModelRouter:
    """Keeps every request on the user-selected model."""

    def route(
        self,
        request: ChatRequest,
        intent: str,
        available_models: tuple[str, ...],
    ) -> ModelRoute:
        del intent, available_models
        return ModelRoute(model=request.model, reason="selected_model")
