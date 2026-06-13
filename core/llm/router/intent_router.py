from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.llm.contracts import AttachmentKind, ChatRequest


@dataclass(frozen=True)
class IntentRoute:
    intent: str
    reason: str


class IntentRouter:
    """Classifies requests with local rules before prompt/model routing."""

    _NAMING_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("naming_function", ("함수명", "함수 이름", "function name")),
        ("naming_method", ("메서드명", "메소드명", "method name")),
        ("naming_variable", ("변수명", "변수 이름", "variable name")),
        ("naming_constant", ("상수명", "상수 이름", "constant name")),
        ("naming_class", ("클래스명", "클래스 이름", "class name")),
        ("naming_interface", ("인터페이스명", "interface name")),
        ("naming_type", ("타입명", "type name")),
        ("naming_file", ("파일명", "파일 이름", "filename", "file name")),
        ("naming_folder", ("폴더명", "폴더 이름", "디렉토리명", "directory name")),
        ("naming_component", ("컴포넌트명", "component name")),
        ("naming_hook", ("훅 이름", "hook name")),
        ("naming_event", ("이벤트명", "event name")),
        ("naming_endpoint", ("엔드포인트명", "endpoint name")),
        ("naming_api", ("api 이름", "api명")),
        ("naming_table", ("테이블명", "table name")),
        ("naming_column", ("컬럼명", "column name")),
        ("naming_branch", ("브랜치명", "branch name")),
        ("naming_pr", ("pr 제목", "pull request 제목", "pull request title")),
        ("naming_test", ("테스트명", "test name")),
        ("naming_package", ("패키지명", "package name")),
        ("naming_env", ("환경변수", "env name", "environment variable")),
        ("naming_css_class", ("css 클래스", "css class")),
    )

    def route(self, request: ChatRequest) -> IntentRoute:
        attachment_route = self._route_attachment(request)
        if attachment_route is not None:
            return attachment_route

        text = _normalize(request.user_message.content)
        if not text:
            return IntentRoute(intent="simple_chat", reason="empty_text")

        if self._contains_any(text, ("커밋 메시지", "commit message", "git commit")):
            return IntentRoute(intent="commit_message", reason="commit_keyword")
        if self._contains_any(text, ("pr 설명", "pr 본문", "pull request", "머지 요청")):
            return IntentRoute(intent="pr_description", reason="pr_keyword")

        naming_route = self._route_naming(text)
        if naming_route is not None:
            return naming_route
        if self._contains_any(text, ("번역", "영어로", "한국어로", "일본어로", "translate")):
            return IntentRoute(intent="translate", reason="translate_keyword")
        if self._contains_any(text, ("명령어", "설치", "실행", "터미널", "command", "cli")):
            return IntentRoute(intent="command", reason="command_keyword")
        if self._contains_any(text, ("고쳐줘", "수정해줘", "버그", "에러", "오류", "fix")):
            return IntentRoute(intent="code_fix", reason="fix_keyword")
        if self._contains_any(text, ("설명해줘", "분석해줘", "이 코드", "코드 설명")):
            return IntentRoute(intent="code_explain", reason="explain_keyword")

        return IntentRoute(intent="simple_chat", reason="fallback")

    def _route_attachment(self, request: ChatRequest) -> IntentRoute | None:
        attachments = request.user_message.attachments
        if not attachments:
            return None

        text = _normalize(request.user_message.content)
        if any(attachment.is_image for attachment in attachments):
            if self._contains_any(text, ("코드", "캡쳐", "캡처", "복사", "텍스트로", "옮겨줘")):
                return IntentRoute(intent="image_code_transcription", reason="image_code_keyword")
            return IntentRoute(intent="image_question", reason="image_attachment")

        if any(
            attachment.kind == AttachmentKind.SPREADSHEET or _attachment_suffix(attachment.path) in {".csv", ".tsv"}
            for attachment in attachments
        ):
            return IntentRoute(intent="spreadsheet_question", reason="spreadsheet_attachment")
        if any(
            attachment.kind in {AttachmentKind.DOCUMENT, AttachmentKind.PRESENTATION, AttachmentKind.TEXT}
            for attachment in attachments
        ):
            return IntentRoute(intent="document_question", reason="document_attachment")

        return None

    def _route_naming(self, text: str) -> IntentRoute | None:
        for intent, keywords in self._NAMING_PATTERNS:
            if self._contains_any(text, keywords):
                return IntentRoute(intent=intent, reason="naming_keyword")

        if not self._contains_any(text, ("추천", "지어", "이름", "name", "naming", "만들어", "뭐가 좋아")):
            return None

        if re.search(r"\b(commit|pr|branch)\b", text):
            return IntentRoute(intent="naming_commit", reason="generic_naming_keyword")
        if "커밋" in text:
            return IntentRoute(intent="naming_commit", reason="generic_naming_keyword")

        return None

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _attachment_suffix(path: str) -> str:
    return Path(path).suffix.lower()
