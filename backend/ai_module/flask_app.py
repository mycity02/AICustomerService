"""Standalone Flask application for the AI module."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, Flask
from pydantic import BaseModel

from web import ApiError, EndpointContext, endpoint, register_error_handlers

from .engine import ai_engine


class AIChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    business_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    purchase_flow: Optional[Dict[str, Any]] = None
    aftersales_flow: Optional[Dict[str, Any]] = None


bp = Blueprint("ai", __name__, url_prefix="/ai")


@bp.get("/health")
@endpoint()
def health(ctx: EndpointContext):
    return {"status": "healthy", "module": "ai", "framework": "Flask"}


@bp.post("/chat")
@endpoint(body=AIChatRequest)
def chat(ctx: EndpointContext):
    try:
        result = ai_engine.process_message(
            user_id=ctx.body.user_id,
            session_id=ctx.body.session_id,
            message=ctx.body.message,
            attachments=ctx.body.attachments,
            purchase_flow=ctx.body.purchase_flow,
            aftersales_flow=ctx.body.aftersales_flow,
            business_id=ctx.body.business_id,
        )
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc
    except Exception as exc:
        raise ApiError(500, "AI module processing failed") from exc
    return {
        "response": result.get("response", ""),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "sources": result.get("sources"),
        "quick_actions": result.get("quick_actions"),
        "recommended_products": result.get("recommended_products"),
        "timestamp": result.get("timestamp", datetime.now().isoformat()),
    }


@bp.get("/businesses")
@endpoint()
def list_businesses(ctx: EndpointContext):
    return {"businesses": ai_engine.list_businesses()}


@bp.get("/businesses/<business_id>")
@endpoint()
def get_business_info(ctx: EndpointContext, business_id: str):
    try:
        return ai_engine.get_business_info(business_id)
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc


@bp.get("/plugins")
@endpoint()
def list_plugins(ctx: EndpointContext):
    try:
        return ai_engine.list_plugins(
            business_id=ctx.query_str("business_id"),
            group=ctx.query_str("group"),
        )
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc


def create_ai_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    register_error_handlers(app)
    app.register_blueprint(bp)
    return app


app = create_ai_app()
