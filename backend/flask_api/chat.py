"""Chat session, messaging, and SSE Flask routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from flask import Blueprint

from ai_module.engine import ai_engine
from database import db_session
from schemas import MessageCreate, SessionCreate, SessionResponse
from services.attachment_service import AttachmentService
from services.message_service import MessageService
from services.order_service import OrderService
from services.session_service import SessionService
from services.smart_questions_service import smart_questions_service
from web import ApiError, EndpointContext, SSEStream, endpoint


logger = logging.getLogger(__name__)
bp = Blueprint("chat", __name__, url_prefix="/chat")
session_service = SessionService()
message_service = MessageService()
attachment_service = AttachmentService()


def _get_owned_session(db, session_id: str, user_id: str) -> SessionResponse:
    session = session_service.get_session(db, session_id, user_id)
    if not session:
        raise ApiError(404, "session not found")
    return session


def _build_session_title(message: str, attachments: List[dict]) -> str | None:
    if message.strip():
        return session_service.generate_session_title(message)
    if attachments:
        file_name = attachments[0].get("file_name") or attachments[0].get("file_id")
        if file_name:
            return session_service.generate_session_title(str(file_name).rsplit(".", 1)[0])
    return None


def _build_assistant_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intent": result.get("intent"),
        "sources": result.get("sources"),
        "ticket_id": result.get("ticket_id"),
        "quick_actions": result.get("quick_actions"),
        "recommended_products": result.get("recommended_products"),
    }


def _persist_user_turn(db, message_data: MessageCreate, user_id: str) -> Tuple[Any, Any, List[dict]]:
    session = _get_owned_session(db, message_data.session_id, user_id)
    user_message = message_service.save_message(
        db,
        session_id=message_data.session_id,
        role="user",
        content=message_data.message,
    )

    normalized_attachments: List[dict] = []
    if message_data.attachments:
        normalized_attachments = attachment_service.normalize_attachments(
            message_data.attachments,
            user_id=user_id,
            session_id=message_data.session_id,
        )
        attachment_service.save_attachments(
            db,
            message_id=user_message.id,
            attachments=message_data.attachments,
            user_id=user_id,
            session_id=message_data.session_id,
            normalized_attachments=normalized_attachments,
        )

    if session.message_count == 0:
        title = _build_session_title(message_data.message, normalized_attachments)
        if title:
            session_service.update_session_title(db, message_data.session_id, title)

    return session, user_message, normalized_attachments


def _persist_assistant_turn(
    db,
    session_id: str,
    content: str,
    metadata: Dict[str, Any],
):
    assistant_message = message_service.save_message(
        db,
        session_id=session_id,
        role="assistant",
        content=content,
        metadata=metadata,
    )
    session_service.update_session_activity(db, session_id)
    return assistant_message


@bp.post("/session")
@endpoint(body=SessionCreate, auth=True)
def create_session(ctx: EndpointContext):
    return session_service.create_session(ctx.db, ctx.user_id, ctx.body)


@bp.get("/sessions")
@endpoint(auth=True)
def list_sessions(ctx: EndpointContext):
    return session_service.list_user_sessions(
        ctx.db,
        ctx.user_id,
        ctx.query_int("limit", 20, minimum=1, maximum=100),
        ctx.query_int("offset", 0, minimum=0),
    )


@bp.get("/session/<session_id>")
@endpoint(auth=True)
def get_session(ctx: EndpointContext, session_id: str):
    return _get_owned_session(ctx.db, session_id, ctx.user_id)


@bp.post("/session/<session_id>/delete")
@endpoint(auth=True)
def remove_session(ctx: EndpointContext, session_id: str):
    if not session_service.delete_session(ctx.db, session_id, ctx.user_id):
        raise ApiError(404, "session not found")
    return {"message": "session deleted"}


@bp.get("/session/<session_id>/messages")
@endpoint(auth=True)
def get_session_messages(ctx: EndpointContext, session_id: str):
    _get_owned_session(ctx.db, session_id, ctx.user_id)
    return message_service.get_session_messages(
        ctx.db,
        session_id,
        ctx.query_int("limit", 100, minimum=1, maximum=500),
    )


@bp.post("/message")
@endpoint(body=MessageCreate, auth=True)
def send_message(ctx: EndpointContext):
    _get_owned_session(ctx.db, ctx.body.session_id, ctx.user_id)
    _, _, attachments = _persist_user_turn(ctx.db, ctx.body, ctx.user_id)
    result = ai_engine.process_message(
        user_id=ctx.user_id,
        session_id=ctx.body.session_id,
        message=ctx.body.message,
        attachments=attachments,
        purchase_flow=ctx.body.purchase_flow,
        aftersales_flow=ctx.body.aftersales_flow,
    )
    assistant = _persist_assistant_turn(
        ctx.db,
        ctx.body.session_id,
        result.get("response", ""),
        _build_assistant_metadata(result),
    )
    return {
        "message_id": assistant.id,
        "content": result.get("response", ""),
        "sources": result.get("sources"),
        "intent": result.get("intent"),
        "ticket_id": result.get("ticket_id"),
        "processing_time": result.get("processing_time"),
        "quick_actions": result.get("quick_actions"),
        "recommended_products": result.get("recommended_products"),
    }


def _stream_message(message_data: MessageCreate, user_id: str):
    full_response = ""
    event_state: Dict[str, Any] = {}

    with db_session() as db:
        try:
            _get_owned_session(db, message_data.session_id, user_id)
            _, _, attachments = _persist_user_turn(db, message_data, user_id)
            db.commit()
        except Exception as exc:
            db.rollback()
            yield {"type": "error", "message": str(exc)}
            yield {"type": "end", "status": "error"}
            return

        yield {"type": "start"}
        try:
            for event in ai_engine.process_message_stream(
                user_id=user_id,
                session_id=message_data.session_id,
                message=message_data.message,
                attachments=attachments,
                purchase_flow=message_data.purchase_flow,
                aftersales_flow=message_data.aftersales_flow,
            ):
                if event.get("type") == "content":
                    full_response += event.get("delta", "")
                elif event.get("type") == "intent":
                    event_state["intent"] = event.get("intent")
                elif event.get("type") == "end":
                    event_state.update(event)
                yield event
        except Exception:
            logger.exception("Streaming chat failed for session=%s", message_data.session_id)
            yield {"type": "error", "message": "stream processing failed"}
            yield {"type": "end", "status": "error"}
            return

        if full_response:
            _persist_assistant_turn(
                db,
                message_data.session_id,
                full_response,
                {
                    "intent": event_state.get("intent"),
                    "sources": event_state.get("sources"),
                    "quick_actions": event_state.get("quick_actions"),
                    "recommended_products": event_state.get("recommended_products"),
                    "ticket_id": event_state.get("ticket_id"),
                },
            )
            db.commit()


@bp.post("/stream")
@endpoint(body=MessageCreate, auth=True)
def stream_message(ctx: EndpointContext):
    # Authentication is completed before the WSGI response starts. The stream
    # owns a new synchronous DB session because the endpoint session closes here.
    return SSEStream(_stream_message(ctx.body, ctx.user_id))


@bp.get("/smart-questions")
@endpoint(auth=True)
def get_smart_questions(ctx: EndpointContext):
    try:
        recent = OrderService(ctx.db).list_orders(user_id=ctx.user_id, page=1, page_size=5)
        orders = [
            {
                "status": order.get("status"),
                "product_name": order.get("items", [{}])[0].get("product_title", "")
                if order.get("items")
                else "",
                "created_at": order.get("created_at"),
            }
            for order in recent.get("items", [])
        ]
        if ctx.query_str("mode", "smart") == "fast":
            return {
                "questions": smart_questions_service.get_rule_based_questions(orders),
                "mode": "fast",
            }
        questions = smart_questions_service.generate_smart_questions(
            user_id=ctx.user_id,
            user_profile={},
            recent_orders=orders,
            browsing_history=None,
        )
        return {"questions": questions, "mode": "smart"}
    except Exception as exc:
        logger.warning("Failed to build smart questions: %s", exc, exc_info=True)
        return {"questions": smart_questions_service.get_default_questions(), "mode": "fallback"}
