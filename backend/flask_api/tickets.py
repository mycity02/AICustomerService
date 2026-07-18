"""Support ticket Flask routes."""
from flask import Blueprint

from schemas import TicketCreate, TicketUpdate
from services.ticket_service import TicketService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("tickets", __name__, url_prefix="/tickets")
ticket_service = TicketService()


@bp.post("")
@endpoint(body=TicketCreate, auth=True)
def create_ticket(ctx: EndpointContext):
    return ticket_service.create_ticket(ctx.db, ctx.user_id, ctx.body)


@bp.get("/<ticket_id>")
@endpoint(auth=True)
def get_ticket(ctx: EndpointContext, ticket_id: str):
    ticket = ticket_service.get_ticket(ctx.db, ticket_id, ctx.user_id)
    if not ticket:
        raise ApiError(404, "工单不存在")
    return ticket


@bp.get("")
@endpoint(auth=True)
def list_tickets(ctx: EndpointContext):
    return ticket_service.list_user_tickets(
        ctx.db,
        ctx.user_id,
        ctx.query_str("status"),
        ctx.query_int("limit", 20, minimum=1, maximum=100),
        ctx.query_int("offset", 0, minimum=0),
    )


@bp.put("/<ticket_id>")
@endpoint(body=TicketUpdate, auth=True)
def update_ticket(ctx: EndpointContext, ticket_id: str):
    if not ctx.body.status:
        raise ApiError(400, "没有提供更新内容")
    try:
        return ticket_service.update_ticket_status(
            ctx.db, ticket_id, ctx.body.status, ctx.user_id, ctx.body.comment
        )
    except ValueError as exc:
        raise ApiError(404, str(exc)) from exc


@bp.get("/<ticket_id>/history")
@endpoint(auth=True)
def get_ticket_history(ctx: EndpointContext, ticket_id: str):
    if not ticket_service.get_ticket(ctx.db, ticket_id, ctx.user_id):
        raise ApiError(404, "工单不存在")
    return ticket_service.get_ticket_history(ctx.db, ticket_id)
