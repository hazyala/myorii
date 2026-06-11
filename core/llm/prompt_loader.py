from __future__ import annotations

from core.paths import resource_path


def load_prompt(*parts: str) -> str:
    prompt_path = resource_path("prompts", *(parts or ("system.md",)))
    return prompt_path.read_text(encoding="utf-8").strip()
