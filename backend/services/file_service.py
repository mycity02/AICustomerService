"""File storage and secure lookup helpers."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from docx import Document as DocxDocument
from pypdf import PdfReader

from config import settings
from .paddleocr_service import vision_llm_service


class FileService:
    """Manage uploaded files and server-side file ownership metadata."""

    IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._pending_analysis: dict[str, Any] = {}
        self._analysis_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="image-analysis")

    def _get_file_extension(self, filename: str) -> str:
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    def _is_allowed_file(self, filename: str) -> bool:
        return self._get_file_extension(filename) in settings.allowed_extensions_list

    def _is_image_file(self, filename: str) -> bool:
        return self._get_file_extension(filename) in self.IMAGE_EXTENSIONS

    def _build_storage_path(self, file_id: str, ext: str) -> Path:
        return self.upload_dir / f"{file_id}.{ext}"

    def _metadata_path(self, file_id: str) -> Path:
        return self.upload_dir / f"{file_id}.meta.json"

    def _analysis_path(self, file_id: str) -> Path:
        return self.upload_dir / f"{file_id}.analysis.json"

    def _write_json(self, path: Path, payload: dict) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.loads(handle.read())
        except Exception:
            return None

    def upload_file(self, file: Any, user_id: str, session_id: str) -> dict:
        if not self._is_allowed_file(file.filename):
            raise ValueError(f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions_list)}")

        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > settings.MAX_FILE_SIZE:
            max_mb = settings.MAX_FILE_SIZE / 1024 / 1024
            raise ValueError(f"File exceeds size limit ({max_mb:.0f}MB)")

        file_id = str(uuid.uuid4())
        ext = self._get_file_extension(file.filename)
        storage_path = self._build_storage_path(file_id, ext)

        with open(storage_path, "wb") as handle:
            handle.write(file.read())

        metadata = {
            "file_id": file_id,
            "user_id": user_id,
            "session_id": session_id or None,
            "file_name": file.filename,
            "file_size": file_size,
            "file_type": ext,
            "mime_type": file.content_type,
            "storage_path": str(storage_path),
        }
        self._write_json(self._metadata_path(file_id), metadata)

        result = {
            "file_id": file_id,
            "file_name": file.filename,
            "file_size": file_size,
            "file_type": ext,
            "mime_type": file.content_type,
            "extracted_text": None,
            "ocr_used": False,
            "analysis_pending": False,
        }

        if self._is_image_file(file.filename) and vision_llm_service.is_available():
            result["analysis_pending"] = True
            self._pending_analysis[file_id] = self._analysis_executor.submit(
                self._analyze_image, file_id
            )

        return result

    def _analyze_image(self, file_id: str) -> None:
        try:
            metadata = self.get_file_metadata(file_id)
            if not metadata:
                return

            file_path = Path(metadata["storage_path"])
            with open(file_path, "rb") as handle:
                image_data = handle.read()

            analysis = vision_llm_service.analyze_image_intent(image_data)
            payload = {
                "file_id": file_id,
                "extracted_text": analysis.get("extracted_text", ""),
                "ocr_used": True,
                "image_intent": analysis.get("intent", "other"),
                "image_description": analysis.get("description", ""),
                "image_reasoning": analysis.get("reasoning", ""),
                "confidence": analysis.get("confidence", 0),
            }
            self._write_json(self._analysis_path(file_id), payload)
        except Exception as exc:
            print(f"Image analysis failed for {file_id}: {exc}")
        finally:
            self._pending_analysis.pop(file_id, None)

    def get_file_metadata(self, file_id: str) -> Optional[dict]:
        metadata = self._read_json(self._metadata_path(file_id))
        if metadata:
            return metadata

        # Backward compatibility for files uploaded before metadata sidecars existed.
        for candidate in self.upload_dir.iterdir():
            if candidate.is_file() and candidate.name.startswith(f"{file_id}.") and not candidate.name.endswith(".json"):
                return {
                    "file_id": file_id,
                    "user_id": None,
                    "session_id": None,
                    "file_name": candidate.name,
                    "file_size": candidate.stat().st_size,
                    "file_type": candidate.suffix.lstrip("."),
                    "mime_type": None,
                    "storage_path": str(candidate.resolve()),
                }
        return None

    def get_owned_file_metadata(
        self,
        file_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Optional[dict]:
        metadata = self.get_file_metadata(file_id)
        if not metadata:
            return None
        if metadata.get("user_id") and metadata["user_id"] != user_id:
            return None
        stored_session_id = metadata.get("session_id")
        if session_id and stored_session_id and stored_session_id != session_id:
            return None
        return metadata

    def resolve_attachment_reference(
        self,
        file_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> dict:
        metadata = self.get_owned_file_metadata(file_id, user_id, session_id=session_id)
        if not metadata:
            raise ValueError(f"Attachment {file_id} was not found for the current user/session")

        return {
            "file_id": metadata["file_id"],
            "file_name": metadata.get("file_name") or file_id,
            "file_type": metadata.get("file_type") or "",
            "file_size": metadata.get("file_size") or 0,
            "mime_type": metadata.get("mime_type"),
            "file_path": metadata["storage_path"],
        }

    def get_image_analysis(
        self,
        file_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[dict]:
        if user_id:
            metadata = self.get_owned_file_metadata(file_id, user_id, session_id=session_id)
            if not metadata:
                return None
        return self._read_json(self._analysis_path(file_id))

    def get_file(
        self,
        file_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[bytes]:
        metadata = (
            self.get_owned_file_metadata(file_id, user_id, session_id=session_id)
            if user_id
            else self.get_file_metadata(file_id)
        )
        if not metadata:
            return None
        with open(metadata["storage_path"], "rb") as handle:
            return handle.read()

    def extract_text(self, file_path: str) -> str:
        ext = self._get_file_extension(file_path)
        try:
            if ext == "pdf":
                return self._extract_pdf_text(file_path)
            if ext in {"doc", "docx"}:
                return self._extract_docx_text(file_path)
            if ext == "txt":
                with open(file_path, "r", encoding="utf-8") as handle:
                    return handle.read()
            return ""
        except Exception as exc:
            print(f"Text extraction failed: {exc}")
            return ""

    def _extract_pdf_text(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    def _extract_docx_text(self, file_path: str) -> str:
        document = DocxDocument(file_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    def analyze_image(self, file_path: str) -> dict:
        try:
            image = Image.open(file_path)
            return {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
            }
        except Exception as exc:
            return {"error": str(exc)}
