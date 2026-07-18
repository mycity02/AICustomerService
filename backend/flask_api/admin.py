"""Administrative Flask routes."""
from datetime import datetime

from flask import Blueprint
from sqlalchemy import func, select

from database.models import Message, Session, Ticket, User
from schemas import SystemConfigUpdate
from services.knowledge_retriever import knowledge_retriever
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _query_datetime(ctx: EndpointContext, name: str) -> datetime | None:
    raw = ctx.query_str(name)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ApiError(422, f"query parameter '{name}' must be an ISO datetime") from exc


@bp.get("/stats")
@endpoint(admin=True)
def get_system_stats(ctx: EndpointContext):
    return {
        "total_users": ctx.db.scalar(select(func.count(User.id))) or 0,
        "total_sessions": ctx.db.scalar(select(func.count(Session.id))) or 0,
        "total_messages": ctx.db.scalar(select(func.count(Message.id))) or 0,
        "total_tickets": ctx.db.scalar(select(func.count(Ticket.id))) or 0,
        "active_sessions": ctx.db.scalar(
            select(func.count(Session.id)).where(Session.is_active.is_(True))
        ) or 0,
        "pending_tickets": ctx.db.scalar(
            select(func.count(Ticket.id)).where(Ticket.status == "pending")
        ) or 0,
    }


@bp.get("/conversations")
@endpoint(admin=True)
def search_conversations(ctx: EndpointContext):
    query = select(Session)
    if user_id := ctx.query_str("user_id"):
        query = query.where(Session.user_id == user_id)
    if start_date := _query_datetime(ctx, "start_date"):
        query = query.where(Session.created_at >= start_date)
    if end_date := _query_datetime(ctx, "end_date"):
        query = query.where(Session.created_at <= end_date)
    query = query.limit(ctx.query_int("limit", 20, minimum=1, maximum=100)).offset(
        ctx.query_int("offset", 0, minimum=0)
    )
    sessions = (ctx.db.execute(query)).scalars().all()
    return {
        "conversations": [
            {
                "session_id": session.id,
                "user_id": session.user_id,
                "message_count": session.message_count,
                "created_at": session.created_at,
                "title": session.title,
            }
            for session in sessions
        ],
        "total": len(sessions),
    }


@bp.post("/knowledge/upload")
@endpoint(admin=True)
def upload_knowledge_document(ctx: EndpointContext):
    uploaded = ctx.file()
    try:
        content = (uploaded.read()).decode("utf-8")
        title = ctx.form.get("title", "") or uploaded.filename
        category = ctx.form.get("category", "")
        ids = knowledge_retriever.add_documents(
            [{
                "content": content,
                "metadata": {
                    "title": title,
                    "category": category,
                    "source": uploaded.filename,
                    "created_by": ctx.user_id,
                },
            }],
            "knowledge_base",
        )
        return {"document_id": ids[0], "title": title, "status": "success"}
    except Exception as exc:
        raise ApiError(500, f"上传失败：{exc}") from exc


@bp.delete("/knowledge/<document_id>")
@endpoint(admin=True)
def delete_knowledge_document(ctx: EndpointContext, document_id: str):
    try:
        knowledge_retriever.delete_document(document_id, "knowledge_base")
        return {"message": "文档已删除"}
    except Exception as exc:
        raise ApiError(500, f"删除失败：{exc}") from exc


@bp.put("/config")
@endpoint(body=SystemConfigUpdate, admin=True)
def update_system_config(ctx: EndpointContext):
    return {"message": "配置已更新", "config": ctx.body.model_dump(exclude_none=True)}
