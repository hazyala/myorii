from __future__ import annotations

import re

from core.llm.contracts import ChatRequest


class ResponseFormatter:
    """Normalizes copy-friendly responses for format-sensitive intents."""

    _BUFFERED_INTENT_PREFIXES = ("naming_",)
    _BUFFERED_INTENTS = {"command", "commit_message"}

    def should_buffer(self, intent: str) -> bool:
        return intent in self._BUFFERED_INTENTS or intent.startswith(self._BUFFERED_INTENT_PREFIXES)

    def format(self, text: str, intent: str, request: ChatRequest) -> str:
        cleaned = text.strip()
        if not cleaned:
            return cleaned

        if intent.startswith("naming_"):
            return self._format_code_candidates(cleaned, request, language=self._language_for_naming(intent))
        if intent == "commit_message":
            return self._format_code_candidates(cleaned, request, language="text")
        if intent == "command":
            return self._format_command(cleaned)
        return cleaned

    def _format_code_candidates(self, text: str, request: ChatRequest, language: str) -> str:
        candidates = self._extract_code_blocks(text) or self._extract_candidate_lines(text)
        limit = self._requested_count(request.user_message.content)
        if limit is not None:
            candidates = candidates[:limit]

        if not candidates:
            return text

        blocks = [f"```{language}\n{candidate}\n```" for candidate in candidates]
        return "가장 무난한 후보입니다.\n\n" + "\n\n".join(blocks)

    def _format_command(self, text: str) -> str:
        if "```" in text:
            return text

        commands = self._extract_candidate_lines(text)
        if not commands:
            return text

        return "\n\n".join(f"```bash\n{command}\n```" for command in commands[:3])

    @staticmethod
    def _extract_code_blocks(text: str) -> list[str]:
        blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", text, flags=re.DOTALL)
        return [_clean_candidate(block) for block in blocks if _clean_candidate(block)]

    @staticmethod
    def _extract_candidate_lines(text: str) -> list[str]:
        candidates: list[str] = []
        for line in text.splitlines():
            candidate = _clean_candidate(line)
            if not candidate:
                continue
            if len(candidate.split()) > 6 and not candidate.startswith(("./", ".venv/", "python", "git ", "npm ")):
                continue
            candidates.append(candidate)
        return _dedupe(candidates)

    @staticmethod
    def _requested_count(text: str) -> int | None:
        match = re.search(r"(\d+)\s*개", text)
        if not match:
            return None
        return max(1, min(int(match.group(1)), 10))

    @staticmethod
    def _language_for_naming(intent: str) -> str:
        if intent in {"naming_file", "naming_folder", "naming_branch", "naming_pr"}:
            return "text"
        if intent == "naming_env":
            return "bash"
        return "python"


def _clean_candidate(text: str) -> str:
    candidate = text.strip()
    candidate = re.sub(r"^[-*]\s+", "", candidate)
    candidate = re.sub(r"^\d+[.)]\s+", "", candidate)
    candidate = candidate.strip("` ")
    if " - " in candidate:
        candidate = candidate.split(" - ", 1)[0].strip()
    if ": " in candidate and not candidate.startswith(("feat:", "fix:", "ui:", "refactor:", "docs:", "chore:")):
        candidate = candidate.split(": ", 1)[0].strip()
    return candidate


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
