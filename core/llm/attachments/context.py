from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AttachmentContext:
    title: str
    body: str
    limitations: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_section(self) -> str:
        lines = [self.title]
        if self.limitations:
            lines.append("제한: " + " ".join(self.limitations))
        if self.warnings:
            lines.append("주의: " + " ".join(self.warnings))
        if self.body:
            lines.append(self.body)
        return "\n".join(lines)
