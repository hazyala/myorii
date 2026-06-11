from __future__ import annotations

import re
from dataclasses import dataclass

from core.llm.contracts import ChatRequest


@dataclass(frozen=True)
class InstantResponse:
    content: str
    intent: str


class InstantRouter:
    """Handles tiny local responses without calling Ollama."""

    _KO_TO_EN = {
        "사과": "apple",
        "바나나": "banana",
        "고양이": "cat",
        "강아지": "dog",
        "물": "water",
        "커피": "coffee",
    }

    _EN_TO_KO = {
        "apple": "사과",
        "banana": "바나나",
        "cat": "고양이",
        "dog": "강아지",
        "water": "물",
        "coffee": "커피",
    }

    _MEAL_SUGGESTIONS = {
        "아침": "계란 토스트 어때요? 빠르고 부담이 적어요.",
        "점심": "김치볶음밥 어때요? 빠르게 먹기 좋고 실패 확률이 낮아요.",
        "저녁": "김치찌개 어때요? 따뜻하고 든든해서 하루 마무리에 좋아요.",
        "야식": "가벼운 우동 어때요? 너무 무겁지 않게 먹기 좋아요.",
    }

    def match(self, request: ChatRequest) -> InstantResponse | None:
        if request.user_message.attachments:
            return None

        text = _normalize(request.user_message.content)
        if not text:
            return None

        translation = self._match_translation(text)
        if translation is not None:
            return translation

        meal = self._match_meal(text)
        if meal is not None:
            return meal

        return self._match_coffee(text)

    def _match_translation(self, text: str) -> InstantResponse | None:
        ko_match = re.fullmatch(r"(.+?)\s*(영어로|영어|in english)", text)
        if ko_match:
            word = ko_match.group(1).strip()
            translated = self._KO_TO_EN.get(word)
            if translated:
                return InstantResponse(content=translated, intent="instant_translate")

        meaning_match = re.fullmatch(r"([a-zA-Z][a-zA-Z\s-]*)\s*(뜻|의미|한국어로)", text)
        if meaning_match:
            word = meaning_match.group(1).strip().lower()
            translated = self._EN_TO_KO.get(word)
            if translated:
                return InstantResponse(content=translated, intent="instant_translate")

        return None

    def _match_meal(self, text: str) -> InstantResponse | None:
        if not any(keyword in text for keyword in ("뭐 먹", "메뉴", "추천")):
            return None

        for meal, suggestion in self._MEAL_SUGGESTIONS.items():
            if meal in text:
                return InstantResponse(content=suggestion, intent="instant_food")

        if "먹" in text:
            return InstantResponse(content=self._MEAL_SUGGESTIONS["점심"], intent="instant_food")

        return None

    def _match_coffee(self, text: str) -> InstantResponse | None:
        if re.fullmatch(r".*커피.*(마실까|먹을까|추천).*", text):
            return InstantResponse(content="마셔도 좋아요. 대신 늦은 시간이면 디카페인으로 가요.", intent="instant_chat")
        return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".?!。？！")
