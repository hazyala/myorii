from __future__ import annotations

from core.paths import resource_path


def load_prompt(name: str = "system.md") -> str:
    return resource_path("prompts", name).read_text(encoding="utf-8").strip()
