"""Attachment persistence and normalization helpers."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Attachment
from .file_service import FileService


class AttachmentService:
    """Resolve attachment references server-side before persistence or AI use."""

    def __init__(self):
        self.file_service = FileService()

    def normalize_attachments(
        self,
        attachments: Iterable[Any],
        user_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for attachment in attachments:
            if hasattr(attachment, "model_dump"):
                payload = attachment.model_dump()
            elif hasattr(attachment, "dict"):
                payload = attachment.dict()
            else:
                payload = dict(attachment)

            file_id = payload.get("file_id")
            if not file_id:
                raise ValueError("Attachment file_id is required")

            resolved = self.file_service.resolve_attachment_reference(
                file_id=file_id,
                user_id=user_id,
                session_id=session_id,
            )
            resolved["file_name"] = payload.get("file_name") or resolved["file_name"]
            resolved["file_type"] = payload.get("file_type") or resolved["file_type"]
            resolved["file_size"] = payload.get("file_size") or resolved["file_size"]
            resolved["extracted_text"] = payload.get("extracted_text")
            resolved["ocr_used"] = bool(payload.get("ocr_used", False))
            resolved["image_intent"] = payload.get("image_intent")
            resolved["image_description"] = payload.get("image_description")
            normalized.append(resolved)

        return normalized

    def save_attachments(
        self,
        db: Session,
        message_id: str,
        attachments: Iterable[Any],
        user_id: str,
        session_id: str,
        normalized_attachments: List[Dict[str, Any]] | None = None,
    ) -> List[Attachment]:
        normalized = normalized_attachments or self.normalize_attachments(
            attachments,
            user_id=user_id,
            session_id=session_id,
        )
        saved: List[Attachment] = []

        for payload in normalized:
            attachment = Attachment(
                id=str(uuid.uuid4()),
                message_id=message_id,
                file_name=payload["file_name"],
                file_type=payload["file_type"],
                file_size=payload["file_size"],
                file_path=payload["file_path"],
                mime_type=self._get_mime_type(payload["file_type"], payload.get("mime_type")),
            )
            db.add(attachment)
            saved.append(attachment)

        db.commit()
        for attachment in saved:
            db.refresh(attachment)

        return saved

    def _get_mime_type(self, file_type: str, fallback: str | None = None) -> str:
        mime_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "md": "text/markdown",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "webp": "image/webp",
        }
        return fallback or mime_types.get((file_type or "").lower(), "application/octet-stream")

    def get_message_attachments(self, db: Session, message_id: str) -> List[Attachment]:
        result = db.execute(
            select(Attachment).where(Attachment.message_id == message_id).order_by(Attachment.created_at)
        )
        return result.scalars().all()
