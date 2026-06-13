from __future__ import annotations

import re

from core.llm.contracts import ChatRequest


class ResponseFormatter:
    """Normalizes copy-friendly responses for format-sensitive intents."""

    _BUFFERED_INTENT_PREFIXES = ("naming_",)
    _ATTACHMENT_INTENTS = {"document_question", "spreadsheet_question", "image_question"}
    _BUFFERED_INTENTS = {"command", "commit_message", "image_code_transcription", *_ATTACHMENT_INTENTS}

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
        if intent == "image_code_transcription":
            return self._format_single_snippet(cleaned)
        if intent in self._ATTACHMENT_INTENTS:
            return self._format_attachment_response(cleaned)
        return cleaned

    def _format_attachment_response(self, text: str) -> str:
        without_code_fences = self._unwrap_nontechnical_code_fences(text)
        without_full_repeat = self._remove_full_repeat(without_code_fences)
        return self._remove_adjacent_repeated_paragraphs(without_full_repeat)

    def _format_code_candidates(self, text: str, request: ChatRequest, language: str) -> str:
        candidates = self._extract_candidate_blocks(text)
        if not candidates:
            candidates = [line for line in self._extract_candidate_lines(text) if _is_candidate_like(line)]
        limit = self._requested_count(request.user_message.content)
        if limit is not None:
            candidates = candidates[:limit]

        if not candidates:
            return text

        blocks = [f"```{language}\n{candidate}\n```" for candidate in candidates]
        return "가장 무난한 후보입니다.\n\n" + "\n\n".join(blocks)

    def _format_command(self, text: str) -> str:
        command_blocks = self._extract_command_blocks(text)
        if command_blocks:
            return "\n\n".join(f"```bash\n{command}\n```" for command in command_blocks)

        if self._has_multiline_code_block(text):
            return text

        commands = self._extract_candidate_lines(text)
        if not commands:
            return text

        return "\n\n".join(f"```bash\n{command}\n```" for command in commands[:3])

    def _format_single_snippet(self, text: str) -> str:
        blocks = self._extract_code_blocks(text)
        if len(blocks) != 1:
            return text

        language, code = blocks[0]
        if not code:
            return text

        return f"```{language}\n{code}\n```" if language else f"```\n{code}\n```"

    @staticmethod
    def _extract_code_blocks(text: str) -> list[tuple[str, str]]:
        blocks = re.findall(r"```([a-zA-Z0-9_-]*)\n(.*?)```", text, flags=re.DOTALL)
        return [(language, code.strip()) for language, code in blocks if code.strip()]

    def _extract_candidate_blocks(self, text: str) -> list[str]:
        candidates: list[str] = []
        for _language, code in self._extract_code_blocks(text):
            code_lines = [_clean_candidate(line) for line in code.splitlines()]
            useful_lines = [line for line in code_lines if _is_candidate_like(line)]
            if useful_lines:
                candidates.extend(useful_lines)
                continue

            candidate = _clean_candidate(code)
            if candidate:
                candidates.append(candidate)
        return _dedupe(candidates)

    def _extract_command_blocks(self, text: str) -> list[str]:
        commands: list[str] = []
        for language, code in self._extract_code_blocks(text):
            if language and language not in {"bash", "sh", "shell", "zsh"}:
                continue
            lines = [_clean_command_line(line) for line in code.splitlines()]
            non_empty_lines = [line for line in lines if line]
            command_lines = [line for line in lines if _is_shell_command(line)]
            if len(command_lines) == 1 and len(non_empty_lines) == 1:
                commands.append(command_lines[0])
            elif len(command_lines) == len(non_empty_lines):
                commands.extend(command_lines)
        return _dedupe(commands)

    @staticmethod
    def _extract_candidate_lines(text: str) -> list[str]:
        candidates: list[str] = []
        for line in text.splitlines():
            candidate = _clean_candidate(line)
            if not candidate:
                continue
            if _is_comment_line(candidate):
                continue
            if len(candidate.split()) > 6 and not _is_shell_command(candidate):
                continue
            candidates.append(candidate)
        return _dedupe(candidates)

    def _has_multiline_code_block(self, text: str) -> bool:
        return any("\n" in code for _language, code in self._extract_code_blocks(text))

    @staticmethod
    def _unwrap_nontechnical_code_fences(text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            language = match.group(1).strip().lower()
            code = match.group(2).strip("\n")
            if _looks_like_code_or_command(code):
                return match.group(0)
            if language in _CODE_FENCE_LANGUAGES:
                return match.group(0)
            return code

        return re.sub(r"```([a-zA-Z0-9_-]*)\n(.*?)```", replace, text, flags=re.DOTALL)

    @staticmethod
    def _remove_full_repeat(text: str) -> str:
        lines = text.splitlines()
        for split in range(1, len(lines)):
            left = [line.strip() for line in lines[:split] if line.strip()]
            right = [line.strip() for line in lines[split:] if line.strip()]
            if left and left == right:
                return "\n".join(lines[:split]).strip()
        return text

    @staticmethod
    def _remove_adjacent_repeated_paragraphs(text: str) -> str:
        paragraphs = [paragraph for paragraph in re.split(r"\n{2,}", text.strip()) if paragraph.strip()]
        if len(paragraphs) <= 1:
            return text.strip()

        result: list[str] = []
        previous = ""
        for paragraph in paragraphs:
            normalized = re.sub(r"\s+", " ", paragraph).strip()
            if normalized == previous:
                continue
            result.append(paragraph.strip())
            previous = normalized
        return "\n\n".join(result)

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
    if " - " in candidate and not _is_shell_command(candidate):
        candidate = candidate.split(" - ", 1)[0].strip()
    if ": " in candidate and not candidate.startswith(("feat:", "fix:", "ui:", "refactor:", "docs:", "chore:")):
        candidate = candidate.split(": ", 1)[0].strip()
    return candidate


def _clean_command_line(text: str) -> str:
    command = text.strip()
    command = re.sub(r"^[-*]\s+", "", command)
    command = re.sub(r"^\d+[.)]\s+", "", command)
    return command.strip("` ")


def _is_candidate_like(text: str) -> bool:
    if not text or _is_comment_line(text):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", text):
        return True
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", text):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", text):
        return True
    if re.fullmatch(r"[a-z0-9][a-z0-9._/-]*\.[a-z0-9]+", text):
        return True
    if re.fullmatch(r"[a-z0-9][a-z0-9._/-]*", text) and any(separator in text for separator in ("-", "/", "_")):
        return True
    if text.startswith(("feat:", "fix:", "ui:", "refactor:", "docs:", "chore:")):
        return True
    return False


def _is_shell_command(text: str) -> bool:
    command_prefixes = (
        "./",
        ".venv/",
        "python",
        "python3",
        "pip",
        "uv ",
        "git ",
        "npm ",
        "pnpm ",
        "yarn ",
        "brew ",
        "curl ",
        "mkdir ",
        "cd ",
        "ollama ",
    )
    return text.startswith(command_prefixes)


def _looks_like_code_or_command(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if any(_is_shell_command(line) for line in lines):
        return True
    if any(re.match(r"^(async\s+def|def|class|function|import|from)\b", line) for line in lines):
        return True
    if any(re.search(r"[{};]|=>|</?\w+|=\s*[^=]", line) for line in lines):
        return True
    return False


_CODE_FENCE_LANGUAGES = {
    "bash",
    "c",
    "cpp",
    "css",
    "go",
    "html",
    "java",
    "javascript",
    "js",
    "jsx",
    "kotlin",
    "kt",
    "php",
    "python",
    "py",
    "rb",
    "rs",
    "rust",
    "scss",
    "sh",
    "shell",
    "sql",
    "swift",
    "tsx",
    "typescript",
    "ts",
    "zsh",
}


def _is_comment_line(text: str) -> bool:
    return text.startswith(("#", "//", "/*", "*", "--"))


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
