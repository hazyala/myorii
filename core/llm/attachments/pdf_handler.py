from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.llm.attachments.context import AttachmentContext
from core.llm.contracts import ChatAttachmentPayload


class PdfHandler:
    """Extracts bounded text from PDF attachments."""

    SUPPORTED_SUFFIXES = {".pdf"}

    def __init__(self, max_pages: int = 5, max_chars: int = 6000) -> None:
        self._max_pages = max_pages
        self._max_chars = max_chars

    def extract(self, attachment: ChatAttachmentPayload) -> AttachmentContext:
        path = Path(attachment.path)
        text, page_count, used_fallback, extraction_warnings = self._extract_text(path)
        body, truncated = self._truncate(text)
        warnings = list(extraction_warnings)
        if used_fallback:
            warnings.append("pypdf를 사용할 수 없어 제한적인 PDF 텍스트 추출을 사용했습니다.")
        if not body:
            if used_fallback:
                warnings.append("pypdf 의존성 누락으로 PDF 텍스트를 충분히 확인하지 못했습니다.")
            else:
                warnings.append("추출 가능한 텍스트가 없습니다. 스캔 PDF이거나 이미지 기반 PDF일 수 있습니다.")
        if truncated:
            warnings.append("본문이 잘렸습니다.")

        summary = [f"읽은 페이지: 최대 {self._max_pages}페이지"]
        if page_count is not None:
            summary.append(f"전체 페이지 추정: {page_count}페이지")
        if body:
            summary.append(body)

        return AttachmentContext(
            title=f"[첨부 PDF: {attachment.name}]",
            body="\n".join(summary),
            limitations=(
                "PDF 첨부는 텍스트 추출만 지원합니다.",
                "스캔 이미지, OCR, 표 구조 보존, 이미지/차트 분석은 지원하지 않습니다.",
            ),
            warnings=tuple(warnings),
            metadata={
                "handler": "PdfHandler",
                "mime_type": attachment.mime_type,
                "max_pages": self._max_pages,
                "truncated": truncated,
                "used_fallback": used_fallback,
            },
        )

    def supports(self, attachment: ChatAttachmentPayload) -> bool:
        return Path(attachment.path).suffix.lower() in self.SUPPORTED_SUFFIXES

    def _extract_text(self, path: Path) -> tuple[str, int | None, bool, tuple[str, ...]]:
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError:
            return self._extract_text_fallback(path), None, True, ()

        try:
            reader = PdfReader(str(path))
            texts = []
            for page in reader.pages[: self._max_pages]:
                texts.append(page.extract_text() or "")
            text = "\n\n".join(text.strip() for text in texts if text.strip())
            if self._is_low_quality_text(text):
                pdfminer_text = self._extract_text_with_pdfminer(path)
                if pdfminer_text and not self._is_low_quality_text(pdfminer_text):
                    return pdfminer_text, len(reader.pages), False, ()
                return "", len(reader.pages), False, (
                    "PDF 텍스트 추출 결과가 깨진 문자 위주라 내용을 충분히 확인하지 못했습니다.",
                )
            return text, len(reader.pages), False, ()
        except Exception:
            return self._extract_text_fallback(path), None, True, ()

    def _extract_text_with_pdfminer(self, path: Path) -> str:
        try:
            from pdfminer.high_level import extract_text  # type: ignore[import-not-found]
        except ImportError:
            return ""

        try:
            text = extract_text(str(path), page_numbers=list(range(self._max_pages)))
        except Exception:
            return ""
        return text.strip()

    def _extract_text_fallback(self, path: Path) -> str:
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise RuntimeError(f"PDF 파일을 읽을 수 없어요: {path.name}") from exc

        text = raw.decode("latin-1", errors="ignore")
        values = re.findall(r"\(([^()]*)\)\s*Tj", text)
        arrays = re.findall(r"\[(.*?)\]\s*TJ", text, flags=re.DOTALL)
        for array in arrays:
            values.extend(re.findall(r"\(([^()]*)\)", array))
        return "\n".join(self._decode_pdf_text(value) for value in values).strip()

    def _decode_pdf_text(self, value: str) -> str:
        replacements: dict[str, str] = {
            r"\(": "(",
            r"\)": ")",
            r"\\": "\\",
            r"\n": "\n",
            r"\r": "\n",
            r"\t": "\t",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        return value

    def _is_low_quality_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text)
        if not normalized:
            return False
        replacement_chars = sum(1 for char in normalized if char in {"■", "□", "\ufffd"})
        readable_chars = sum(1 for char in normalized if char.isalnum() or "\uac00" <= char <= "\ud7a3")
        if replacement_chars >= 3 and replacement_chars / len(normalized) >= 0.2:
            return True
        return len(normalized) >= 20 and readable_chars / len(normalized) < 0.2

    def _truncate(self, text: str) -> tuple[str, bool]:
        normalized = text.strip()
        if len(normalized) <= self._max_chars:
            return normalized, False
        return f"{normalized[:self._max_chars].rstrip()}\n\n...[내용 일부 생략]", True
