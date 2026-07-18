"""Knowledge-base Flask routes."""
from flask import Blueprint

from services.knowledge_service import knowledge_service
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")


@bp.post("/upload")
@endpoint(auth=True)
def upload_knowledge_document(ctx: EndpointContext):
    try:
        result = knowledge_service.upload_document(
            file=ctx.file(),
            user_id=ctx.user_id,
            title=ctx.form.get("title") or None,
            description=ctx.form.get("description") or None,
        )
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    except Exception as exc:
        raise ApiError(500, f"上传失败：{exc}") from exc
    return {
        "id": result["doc_id"],
        "title": result["title"],
        "description": result["description"],
        "file_name": result["file_name"],
        "file_type": result["file_type"],
        "file_size": result["file_size"],
        "chunk_count": result["chunk_count"],
        "created_by": ctx.user_id,
        "status": "active",
        "created_at": None,
    }


@bp.get("/documents")
@endpoint(auth=True)
def list_knowledge_documents(ctx: EndpointContext):
    try:
        documents = knowledge_service.list_documents()
    except Exception as exc:
        raise ApiError(500, f"获取文档列表失败：{exc}") from exc
    return [
        {
            "id": doc["doc_id"],
            "title": doc.get("title", doc["file_name"]),
            "description": doc.get("description", ""),
            "file_name": doc["file_name"],
            "file_type": doc["file_type"],
            "file_size": doc["file_size"],
            "chunk_count": doc.get("chunk_count", 0),
            "created_by": ctx.user_id,
            "status": "active",
            "created_at": doc.get("created_at"),
        }
        for doc in documents
    ]


@bp.delete("/documents/<doc_id>")
@endpoint(auth=True)
def delete_knowledge_document(ctx: EndpointContext, doc_id: str):
    try:
        success = knowledge_service.delete_document(doc_id)
    except Exception as exc:
        raise ApiError(500, f"删除失败：{exc}") from exc
    if not success:
        raise ApiError(404, "文档不存在或删除失败")
    return {"message": "文档删除成功", "doc_id": doc_id}
