from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from core.llm.attachments.context import AttachmentContext
from core.llm.contracts import ChatAttachmentPayload


class XlsxHandler:
    """Summarizes XLSX sheets by names, columns, and sample rows."""

    SUPPORTED_SUFFIXES = {".xlsx"}
    _NS = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
        "docrel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    def __init__(self, max_sheets: int = 3, sample_rows: int = 5, max_cell_chars: int = 120) -> None:
        self._max_sheets = max_sheets
        self._sample_rows = sample_rows
        self._max_cell_chars = max_cell_chars

    def extract(self, attachment: ChatAttachmentPayload) -> AttachmentContext:
        path = Path(attachment.path)
        summaries, sheet_count = self._extract_summaries(path)
        body = "\n\n".join(summaries)
        warnings = ()
        if sheet_count > self._max_sheets:
            warnings = (f"시트가 {sheet_count}개라 앞쪽 {self._max_sheets}개만 읽었습니다.",)

        return AttachmentContext(
            title=f"[첨부 XLSX: {attachment.name}]",
            body=body,
            limitations=(
                "XLSX 첨부는 시트명, 컬럼명, 샘플 행만 읽습니다.",
                "전체 행 분석, 수식 재계산, 피벗/차트/서식 분석은 지원하지 않습니다.",
            ),
            warnings=warnings,
            metadata={
                "handler": "XlsxHandler",
                "mime_type": attachment.mime_type,
                "sheet_count": sheet_count,
                "sample_rows": self._sample_rows,
            },
        )

    def supports(self, attachment: ChatAttachmentPayload) -> bool:
        return Path(attachment.path).suffix.lower() in self.SUPPORTED_SUFFIXES

    def _extract_summaries(self, path: Path) -> tuple[list[str], int]:
        try:
            with ZipFile(path) as archive:
                shared_strings = self._shared_strings(archive)
                sheets = self._sheets(archive)
                summaries = [
                    self._sheet_summary(archive, sheet_name, sheet_path, shared_strings)
                    for sheet_name, sheet_path in sheets[: self._max_sheets]
                ]
        except (BadZipFile, KeyError, OSError, ElementTree.ParseError) as exc:
            raise RuntimeError(f"XLSX 파일을 읽을 수 없어요: {path.name}") from exc
        return summaries, len(sheets)

    def _shared_strings(self, archive: ZipFile) -> list[str]:
        try:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        values: list[str] = []
        for item in root.findall("main:si", self._NS):
            parts = [node.text or "" for node in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
            values.append("".join(parts))
        return values

    def _sheets(self, archive: ZipFile) -> list[tuple[str, str]]:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("rel:Relationship", self._NS)
            if "Id" in rel.attrib and "Target" in rel.attrib
        }
        sheets: list[tuple[str, str]] = []
        for sheet in workbook.findall("main:sheets/main:sheet", self._NS):
            name = sheet.attrib.get("name", "Sheet")
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = targets.get(rel_id or "")
            if target:
                sheets.append((name, "xl/" + target.lstrip("/")))
        return sheets

    def _sheet_summary(
        self,
        archive: ZipFile,
        sheet_name: str,
        sheet_path: str,
        shared_strings: list[str],
    ) -> str:
        root = ElementTree.fromstring(archive.read(sheet_path))
        rows = []
        for row in root.findall("main:sheetData/main:row", self._NS):
            values = [self._cell_value(cell, shared_strings) for cell in row.findall("main:c", self._NS)]
            if any(values):
                rows.append(values)
            if len(rows) >= self._sample_rows + 1:
                break

        if not rows:
            return f"시트: {sheet_name}\n샘플 행: 없음"

        columns = rows[0]
        sample_rows = rows[1:]
        lines = [f"시트: {sheet_name}", "컬럼: " + ", ".join(columns)]
        if not sample_rows:
            lines.append("샘플 행: 없음")
            return "\n".join(lines)

        lines.append("샘플 행:")
        for index, row in enumerate(sample_rows, start=1):
            pairs = []
            for cell_index, value in enumerate(row):
                column = columns[cell_index] if cell_index < len(columns) and columns[cell_index] else f"column_{cell_index + 1}"
                pairs.append(f"{column}: {self._truncate_cell(value)}")
            lines.append(f"{index}. " + " | ".join(pairs))
        return "\n".join(lines)

    def _cell_value(self, cell: ElementTree.Element, shared_strings: list[str]) -> str:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            parts = [node.text or "" for node in cell.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
            return "".join(parts).strip()

        value = cell.find("main:v", self._NS)
        if value is None or value.text is None:
            return ""
        if cell_type == "s":
            try:
                return shared_strings[int(value.text)].strip()
            except (ValueError, IndexError):
                return ""
        return value.text.strip()

    def _truncate_cell(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip())
        if len(normalized) <= self._max_cell_chars:
            return normalized
        return normalized[: self._max_cell_chars].rstrip() + "..."
