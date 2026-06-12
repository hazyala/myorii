from __future__ import annotations

from core.llm.attachments.context import AttachmentContext
from core.llm.attachments.csv_handler import CsvHandler
from core.llm.attachments.docx_handler import DocxHandler
from core.llm.attachments.pdf_handler import PdfHandler
from core.llm.attachments.text_handler import TextHandler
from core.llm.attachments.xlsx_handler import XlsxHandler
from core.llm.contracts import ChatAttachmentPayload


class AttachmentRouter:
    """Builds model-ready context from supported non-image attachments."""

    def __init__(
        self,
        text_handler: TextHandler | None = None,
        csv_handler: CsvHandler | None = None,
        docx_handler: DocxHandler | None = None,
        pdf_handler: PdfHandler | None = None,
        xlsx_handler: XlsxHandler | None = None,
    ) -> None:
        self._csv_handler = csv_handler or CsvHandler()
        self._docx_handler = docx_handler or DocxHandler()
        self._pdf_handler = pdf_handler or PdfHandler()
        self._text_handler = text_handler or TextHandler()
        self._xlsx_handler = xlsx_handler or XlsxHandler()

    def build_contexts(self, attachments: tuple[ChatAttachmentPayload, ...]) -> tuple[AttachmentContext, ...]:
        contexts: list[AttachmentContext] = []
        for attachment in attachments:
            if attachment.is_image:
                continue
            if self._csv_handler.supports(attachment):
                contexts.append(self._csv_handler.extract(attachment))
            elif self._docx_handler.supports(attachment):
                contexts.append(self._docx_handler.extract(attachment))
            elif self._pdf_handler.supports(attachment):
                contexts.append(self._pdf_handler.extract(attachment))
            elif self._xlsx_handler.supports(attachment):
                contexts.append(self._xlsx_handler.extract(attachment))
            elif self._text_handler.supports(attachment):
                contexts.append(self._text_handler.extract(attachment))
        return tuple(contexts)
