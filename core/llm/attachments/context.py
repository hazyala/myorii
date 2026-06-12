from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AttachmentContext:
    title: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_section(self) -> str:
        if not self.body:
            return self.title
        return f"{self.title}\n{self.body}"
