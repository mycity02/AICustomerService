"""Business-pack AI gateway Flask routes."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint
from pydantic import BaseModel

from ai_module.engine import ai_engine
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("gateway", __name__, url_prefix="/v1/gateway")


class ChatRequest(BaseModel):
    business_id: str
    session_id: str
    message: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


@bp.post("/chat/message")
@endpoint(body=ChatRequest, auth=True)
def send_message(ctx: EndpointContext):
    if ctx.body.user_id and ctx.body.user_id != ctx.user_id:
        raise ApiError(403, "request user_id does not match the authenticated user")
    try:
        workflow = ai_engine.get_workflow(ctx.body.business_id)
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc
    try:
        result = workflow.process_message(
            user_id=ctx.user_id,
            session_id=ctx.body.session_id,
            message=ctx.body.message,
            attachments=ctx.body.attachments,
        )
    except Exception as exc:
        raise ApiError(500, "AI gateway processing failed") from exc
    return {
        "message_id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "response": result.get("response", ""),
        "quick_actions": result.get("quick_actions"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "sources": result.get("sources"),
        "recommended_products": result.get("recommended_products"),
        "timestamp": result.get("timestamp", datetime.now().isoformat()),
    }


@bp.get("/businesses")
@endpoint(auth=True)
def list_businesses(ctx: EndpointContext):
    return {"businesses": ai_engine.list_businesses()}


@bp.get("/businesses/<business_id>")
@endpoint(auth=True)
def get_business_info(ctx: EndpointContext, business_id: str):
    try:
        return ai_engine.get_business_info(business_id)
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc


@bp.get("/plugins")
@endpoint(auth=True)
def list_plugins(ctx: EndpointContext):
    try:
        return ai_engine.list_plugins(
            business_id=ctx.query_str("business_id"),
            group=ctx.query_str("group"),
        )
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc
