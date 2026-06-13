from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from core.llm.attachments.context import AttachmentContext
from core.llm.contracts import ChatAttachmentPayload


class DocxHandler:
    """Extracts bounded text from DOCX paragraphs and tables."""

    SUPPORTED_SUFFIXES = {".docx"}
    _TEXT_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"

    def __init__(self, max_chars: int = 6000) -> None:
        self._max_chars = max_chars

    def extract(self, attachment: ChatAttachmentPayload) -> AttachmentContext:
        path = Path(attachment.path)
        text = self._extract_text(path)
        body, truncated = self._truncate(text)
        warnings = []
        if not body:
            warnings.append("추출 가능한 문서 텍스트가 없습니다.")
        if truncated:
            warnings.append("본문이 잘렸습니다.")

        return AttachmentContext(
            title=f"[첨부 DOCX: {attachment.name}]",
            body=body,
            limitations=(
                "DOCX 첨부는 문단과 표 안의 텍스트 일부만 읽습니다.",
                "서식, 이미지, 주석, 변경 추적, 매크로는 분석하지 않습니다.",
            ),
            warnings=tuple(warnings),
            metadata={
                "handler": "DocxHandler",
                "mime_type": attachment.mime_type,
                "truncated": truncated,
            },
        )

    def supports(self, attachment: ChatAttachmentPayload) -> bool:
        return Path(attachment.path).suffix.lower() in self.SUPPORTED_SUFFIXES

    def _extract_text(self, path: Path) -> str:
        try:
            with ZipFile(path) as archive:
                xml = archive.read("word/document.xml")
        except (BadZipFile, KeyError, OSError) as exc:
            raise RuntimeError(f"DOCX 파일을 읽을 수 없어요: {path.name}") from exc

        root = ElementTree.fromstring(xml)
        texts = [node.text.strip() for node in root.iter(self._TEXT_TAG) if node.text and node.text.strip()]
        return "\n".join(texts)

    def _truncate(self, text: str) -> tuple[str, bool]:
        normalized = text.strip()
        if len(normalized) <= self._max_chars:
            return normalized, False
        return f"{normalized[:self._max_chars].rstrip()}\n\n...[내용 일부 생략]", True
