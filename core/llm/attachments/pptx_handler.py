from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from core.llm.attachments.context import AttachmentContext
from core.llm.contracts import ChatAttachmentPayload


class PptxHandler:
    """Extracts slide text from PPTX files for lightweight summaries."""

    SUPPORTED_SUFFIXES = {".pptx"}
    _TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"

    def __init__(self, max_slides: int = 10, max_chars: int = 6000) -> None:
        self._max_slides = max_slides
        self._max_chars = max_chars

    def extract(self, attachment: ChatAttachmentPayload) -> AttachmentContext:
        path = Path(attachment.path)
        slide_texts = self._extract_slide_texts(path)
        body, truncated = self._format_body(slide_texts)
        warnings = []
        if len(slide_texts) > self._max_slides:
            warnings.append(f"슬라이드가 {len(slide_texts)}개라 앞쪽 {self._max_slides}개만 읽었습니다.")
        if not body:
            warnings.append("추출 가능한 슬라이드 텍스트가 없습니다.")
        if truncated:
            warnings.append("본문이 잘렸습니다.")

        return AttachmentContext(
            title=f"[첨부 PPTX: {attachment.name}]",
            body=body,
            limitations=(
                "PPTX 첨부는 슬라이드별 텍스트만 읽습니다.",
                "PPT 제작, 디자인 생성, 이미지/차트/표 구조 분석, 발표자 노트, 수치 계산은 지원하지 않습니다.",
            ),
            warnings=tuple(warnings),
            metadata={
                "handler": "PptxHandler",
                "mime_type": attachment.mime_type,
                "slide_count": len(slide_texts),
                "max_slides": self._max_slides,
                "truncated": truncated,
            },
        )

    def supports(self, attachment: ChatAttachmentPayload) -> bool:
        return Path(attachment.path).suffix.lower() in self.SUPPORTED_SUFFIXES

    def _extract_slide_texts(self, path: Path) -> list[tuple[int, list[str]]]:
        try:
            with ZipFile(path) as archive:
                slide_paths = sorted(
                    (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                    key=self._slide_number,
                )
                return [(self._slide_number(name), self._slide_text(archive, name)) for name in slide_paths]
        except (BadZipFile, OSError, ElementTree.ParseError) as exc:
            raise RuntimeError(f"PPTX 파일을 읽을 수 없어요: {path.name}") from exc

    def _slide_text(self, archive: ZipFile, name: str) -> list[str]:
        root = ElementTree.fromstring(archive.read(name))
        return [node.text.strip() for node in root.iter(self._TEXT_TAG) if node.text and node.text.strip()]

    def _format_body(self, slide_texts: list[tuple[int, list[str]]]) -> tuple[str, bool]:
        lines = [f"전체 슬라이드: {len(slide_texts)}개"]
        for slide_number, texts in slide_texts[: self._max_slides]:
            if texts:
                lines.append(f"슬라이드 {slide_number}: " + " / ".join(texts))
            else:
                lines.append(f"슬라이드 {slide_number}: 텍스트 없음")

        body = "\n".join(lines).strip()
        if len(body) <= self._max_chars:
            return body, False
        return f"{body[:self._max_chars].rstrip()}\n\n...[내용 일부 생략]", True

    def _slide_number(self, name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0
