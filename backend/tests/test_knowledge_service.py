import json
import os
import sys
import types
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_backend_dir = os.path.join(os.path.dirname(__file__), "..")

for pkg in ["backend", "backend.services", "services"]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

_config_path = os.path.join(_backend_dir, "config.py")
_config_spec = importlib.util.spec_from_file_location("backend.config", _config_path)
_config_mod = importlib.util.module_from_spec(_config_spec)
sys.modules["backend.config"] = _config_mod
sys.modules["config"] = _config_mod
_config_spec.loader.exec_module(_config_mod)

_kr_stub = types.ModuleType("backend.services.knowledge_retriever")
_kr_stub.knowledge_retriever = SimpleNamespace(
    available=True,
    delete_by_metadata=MagicMock(return_value=0),
    delete_documents=MagicMock(return_value=0),
    add_documents=MagicMock(return_value=[]),
)
sys.modules["backend.services.knowledge_retriever"] = _kr_stub
sys.modules["services.knowledge_retriever"] = _kr_stub

_service_path = os.path.join(_backend_dir, "services", "knowledge_service.py")
_service_spec = importlib.util.spec_from_file_location(
    "backend.services.knowledge_service",
    _service_path,
)
_service_mod = importlib.util.module_from_spec(_service_spec)
_service_mod.__package__ = "backend.services"
sys.modules["backend.services.knowledge_service"] = _service_mod
_service_spec.loader.exec_module(_service_mod)

KnowledgeService = _service_mod.KnowledgeService


@pytest.fixture
def service(tmp_path: Path):
    svc = KnowledgeService()
    svc.upload_dir = tmp_path / "canonical"
    svc.upload_dir.mkdir()
    svc.metadata_file = svc.upload_dir / "metadata.json"
    svc.metadata = {}
    svc.legacy_upload_dirs = []
    return svc
def test_reindex_documents_backfills_legacy_file(service, monkeypatch):
    legacy_dir = service.upload_dir.parent / "legacy"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "legacy.txt"
    legacy_file.write_text("订单查询相关的知识库内容", encoding="utf-8")
    service.legacy_upload_dirs = [legacy_dir]

    fake_retriever = SimpleNamespace(
        available=True,
        delete_by_metadata=MagicMock(return_value=0),
        delete_documents=MagicMock(return_value=0),
        add_documents=MagicMock(return_value=["legacy_0"]),
    )
    monkeypatch.setattr(_service_mod, "knowledge_retriever", fake_retriever)

    result = service.reindex_documents(force=False)

    assert result["legacy_imported_count"] == 1
    assert result["indexed_count"] == 1
    fake_retriever.add_documents.assert_called_once()
    assert (service.upload_dir / "legacy.txt").exists()
    assert service.metadata["legacy"]["chunk_ids"] == ["legacy_0"]

    saved_metadata = json.loads(service.metadata_file.read_text(encoding="utf-8"))
    assert saved_metadata["legacy"]["indexed"] is True
def test_delete_document_removes_all_chunk_ids(service, monkeypatch):
    doc_file = service.upload_dir / "doc.txt"
    doc_file.write_text("文档内容", encoding="utf-8")

    service.metadata = {
        "doc": {
            "doc_id": "doc",
            "original_filename": "doc.txt",
            "title": "doc.txt",
            "description": "",
            "file_type": "txt",
            "file_size": doc_file.stat().st_size,
            "chunk_count": 2,
            "chunk_ids": ["doc_0", "doc_1"],
            "uploaded_by": "tester",
            "indexed": True,
            "index_error": "",
        }
    }
    service._save_metadata()

    fake_retriever = SimpleNamespace(
        available=True,
        delete_documents=MagicMock(return_value=2),
        delete_by_metadata=MagicMock(return_value=0),
    )
    monkeypatch.setattr(_service_mod, "knowledge_retriever", fake_retriever)

    deleted = service.delete_document("doc")

    assert deleted is True
    fake_retriever.delete_documents.assert_called_once_with(["doc_0", "doc_1"], "knowledge_base")
    assert not doc_file.exists()
    assert "doc" not in service.metadata

