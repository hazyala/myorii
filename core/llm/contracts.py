from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from mimetypes import guess_type
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4


MessageRole = Literal["system", "user", "assistant"]


class AttachmentKind(StrEnum):
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    OTHER = "other"


class SyncState(StrEnum):
    LOCAL_ONLY = "local_only"
    PENDING_UPLOAD = "pending_upload"
    SYNCED = "synced"
    PENDING_DELETE = "pending_delete"
    CONFLICTED = "conflicted"


@dataclass(frozen=True)
class DeviceContext:
    """Request origin metadata for future account and multi-device sync."""

    device_id: str | None = None
    account_id: str | None = None
    user_id: str | None = None
    online: bool = False
    sync_enabled: bool = False


@dataclass(frozen=True)
class SyncMetadata:
    """Stable local/cloud identity fields shared by messages and attachments."""

    local_id: str = field(default_factory=lambda: str(uuid4()))
    cloud_id: str | None = None
    revision: int = 0
    state: SyncState = SyncState.LOCAL_ONLY
    updated_at: str = field(default_factory=lambda: _utc_now())
    last_synced_at: str | None = None


@dataclass(frozen=True)
class ChatAttachmentPayload:
    path: str
    name: str
    mime_type: str
    kind: AttachmentKind = AttachmentKind.OTHER
    size_bytes: int | None = None
    checksum: str | None = None
    sync: SyncMetadata = field(default_factory=SyncMetadata)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_image(self) -> bool:
        return self.kind == AttachmentKind.IMAGE or self.mime_type.startswith("image/")

    @classmethod
    def from_path(cls, path: str | Path) -> ChatAttachmentPayload:
        file_path = Path(path)
        mime_type = guess_type(file_path.name)[0] or "application/octet-stream"
        return cls(
            path=str(file_path),
            name=file_path.name,
            mime_type=mime_type,
            kind=_attachment_kind(file_path.suffix.lower(), mime_type),
            size_bytes=file_path.stat().st_size if file_path.exists() else None,
        )


@dataclass(frozen=True)
class ChatMessagePayload:
    role: MessageRole
    content: str
    attachments: tuple[ChatAttachmentPayload, ...] = ()
    sync: SyncMetadata = field(default_factory=SyncMetadata)
    created_at: str = field(default_factory=lambda: _utc_now())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatRequest:
    model: str
    user_message: ChatMessagePayload
    system_prompt: str = ""
    history: tuple[ChatMessagePayload, ...] = ()
    session_id: str | None = None
    request_id: str = field(default_factory=lambda: str(uuid4()))
    device: DeviceContext = field(default_factory=DeviceContext)
    created_at: str = field(default_factory=lambda: _utc_now())
    metadata: dict[str, Any] = field(default_factory=dict)

    def messages(self) -> list[ChatMessagePayload]:
        messages: list[ChatMessagePayload] = []
        if self.system_prompt:
            messages.append(ChatMessagePayload(role="system", content=self.system_prompt))
        messages.extend(self.history)
        messages.append(self.user_message)
        return messages


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _attachment_kind(suffix: str, mime_type: str) -> AttachmentKind:
    if mime_type.startswith("image/"):
        return AttachmentKind.IMAGE
    if mime_type.startswith("text/") or suffix in {".md", ".json", ".yaml", ".yml", ".csv", ".tsv"}:
        return AttachmentKind.TEXT
    if suffix in {".xls", ".xlsx"}:
        return AttachmentKind.SPREADSHEET
    if suffix in {".ppt", ".pptx"}:
        return AttachmentKind.PRESENTATION
    if suffix in {".doc", ".docx", ".hwp", ".hwpx", ".pdf", ".rtf"}:
        return AttachmentKind.DOCUMENT
    return AttachmentKind.OTHER
