"""Refund Flask routes."""
from flask import Blueprint

from services.refund_service import RefundService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("refunds", __name__, url_prefix="/refunds")


@bp.get("")
@bp.get("/")
@endpoint(auth=True)
def list_refunds(ctx: EndpointContext):
    return RefundService(ctx.db).list_refunds(
        ctx.user_id,
        ctx.query_int("page", 1, minimum=1),
        ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )


@bp.get("/<refund_id>")
@endpoint(auth=True)
def get_refund(ctx: EndpointContext, refund_id: str):
    refund = RefundService(ctx.db).get_refund(refund_id)
    if not refund:
        raise ApiError(404, "售后单不存在")
    return refund
