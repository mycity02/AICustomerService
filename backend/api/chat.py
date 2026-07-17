"""Chat session and messaging endpoints."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from ai_module.engine import ai_engine
from database import get_db
from schemas import ConversationResponse, MessageCreate, MessageResponse, SessionCreate, SessionResponse
from services.attachment_service import AttachmentService
from services.auth_service import AuthService
from services.message_service import MessageService
from services.session_service import SessionService
from services.smart_questions_service import smart_questions_service

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()
session_service = SessionService()
message_service = MessageService()
attachment_service = AttachmentService()


def _get_default_workflow():
    return ai_engine.get_workflow()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    try:
        user = await auth_service.get_current_user(db, credentials.credentials)
        return user.id
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


async def _get_owned_session(db: AsyncSession, session_id: str, user_id: str) -> SessionResponse:
    session = await session_service.get_session(db, session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session not found",
        )
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


async def _persist_user_turn(
    db: AsyncSession,
    message_data: MessageCreate,
    user_id: str,
) -> Tuple[SessionResponse, MessageResponse, List[dict]]:
    session = await _get_owned_session(db, message_data.session_id, user_id)
    user_message = await message_service.save_message(
        db,
        session_id=message_data.session_id,
        role="user",
        content=message_data.message,
    )

    normalized_attachments: List[dict] = []
    if message_data.attachments:
        normalized_attachments = await attachment_service.normalize_attachments(
            message_data.attachments,
            user_id=user_id,
            session_id=message_data.session_id,
        )
        await attachment_service.save_attachments(
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
            await session_service.update_session_title(db, message_data.session_id, title)

    return session, user_message, normalized_attachments


async def _persist_assistant_turn(
    db: AsyncSession,
    session_id: str,
    content: str,
    metadata: Dict[str, Any],
):
    assistant_message = await message_service.save_message(
        db,
        session_id=session_id,
        role="assistant",
        content=content,
        metadata=metadata,
    )
    await session_service.update_session_activity(db, session_id)
    return assistant_message


@router.post("/session", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await session_service.create_session(db, user_id, session_data)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await session_service.list_user_sessions(db, user_id, limit, offset)


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await _get_owned_session(db, session_id, user_id)


@router.post("/session/{session_id}/delete")
async def remove_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    deleted = await session_service.delete_session(db, session_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session not found",
        )
    return {"message": "session deleted"}


@router.get("/session/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_session(db, session_id, user_id)
    return await message_service.get_session_messages(db, session_id, limit)


@router.post("/message", response_model=ConversationResponse)
async def send_message(
    message_data: MessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_session(db, message_data.session_id, user_id)
    _, _, normalized_attachments = await _persist_user_turn(db, message_data, user_id)

    workflow = _get_default_workflow()
    result = await workflow.process_message(
        user_id=user_id,
        session_id=message_data.session_id,
        message=message_data.message,
        attachments=normalized_attachments,
        purchase_flow=message_data.purchase_flow,
        aftersales_flow=message_data.aftersales_flow,
    )

    assistant_message = await _persist_assistant_turn(
        db,
        session_id=message_data.session_id,
        content=result.get("response", ""),
        metadata=_build_assistant_metadata(result),
    )

    return ConversationResponse(
        message_id=assistant_message.id,
        content=result.get("response", ""),
        sources=result.get("sources"),
        intent=result.get("intent"),
        ticket_id=result.get("ticket_id"),
        processing_time=result.get("processing_time"),
        quick_actions=result.get("quick_actions"),
        recommended_products=result.get("recommended_products"),
    )


class SSEResponse(Response):
    def __init__(self, handler, status_code: int = 200):
        self.handler = handler
        self.status_code = status_code
        self.background = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [
                    [b"content-type", b"text/event-stream; charset=utf-8"],
                    [b"cache-control", b"no-cache, no-store"],
                    [b"connection", b"keep-alive"],
                    [b"x-accel-buffering", b"no"],
                ],
            }
        )

        async def send_event(data: dict):
            payload = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            await send(
                {
                    "type": "http.response.body",
                    "body": payload.encode("utf-8"),
                    "more_body": True,
                }
            )

        await self.handler(send_event)
        await send({"type": "http.response.body", "body": b"", "more_body": False})


@router.post("/stream")
async def stream_message(
    message_data: MessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_session(db, message_data.session_id, user_id)

    async def handle_stream(send_event):
        try:
            _, _, normalized_attachments = await _persist_user_turn(db, message_data, user_id)
        except ValueError as exc:
            await send_event({"type": "error", "message": str(exc)})
            await send_event({"type": "end", "status": "error"})
            return

        workflow = _get_default_workflow()
        full_response = ""
        event_state: Dict[str, Any] = {}

        await send_event({"type": "start"})
        try:
            async for event in workflow.process_message_stream(
                user_id=user_id,
                session_id=message_data.session_id,
                message=message_data.message,
                attachments=normalized_attachments,
                purchase_flow=message_data.purchase_flow,
                aftersales_flow=message_data.aftersales_flow,
            ):
                if event.get("type") == "content":
                    full_response += event.get("delta", "")
                elif event.get("type") == "intent":
                    event_state["intent"] = event.get("intent")
                elif event.get("type") == "end":
                    event_state.update(event)
                await send_event(event)
        except Exception as exc:
            logger.exception("Streaming chat failed for session=%s", message_data.session_id)
            await send_event({"type": "error", "message": "stream processing failed"})
            await send_event({"type": "end", "status": "error"})
            return

        if full_response:
            await _persist_assistant_turn(
                db,
                session_id=message_data.session_id,
                content=full_response,
                metadata={
                    "intent": event_state.get("intent"),
                    "sources": event_state.get("sources"),
                    "quick_actions": event_state.get("quick_actions"),
                    "recommended_products": event_state.get("recommended_products"),
                    "ticket_id": event_state.get("ticket_id"),
                },
            )

    return SSEResponse(handle_stream)


@router.get("/smart-questions")
async def get_smart_questions(
    mode: str = "smart",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        from services.order_service import OrderService

        order_service = OrderService(db)
        recent_orders_result = await order_service.list_orders(user_id=user_id, page=1, page_size=5)
        recent_orders = recent_orders_result.get("items", [])

        order_data = []
        for order in recent_orders:
            order_data.append(
                {
                    "status": order.get("status"),
                    "product_name": order.get("items", [{}])[0].get("product_title", "")
                    if order.get("items")
                    else "",
                    "created_at": order.get("created_at"),
                }
            )

        if mode == "fast":
            questions = smart_questions_service.get_rule_based_questions(order_data)
            return {"questions": questions, "mode": "fast"}

        questions = await smart_questions_service.generate_smart_questions(
            user_id=user_id,
            user_profile={},
            recent_orders=order_data,
            browsing_history=None,
        )
        return {"questions": questions, "mode": "smart"}
    except Exception as exc:
        logger.warning("Failed to build smart questions: %s", exc, exc_info=True)
        return {
            "questions": smart_questions_service.get_default_questions(),
            "mode": "fallback",
        }
