"""Order and payment Flask routes."""
from typing import List

from flask import Blueprint
from pydantic import BaseModel

from services.order_service import OrderService
from services.payment_service import PaymentService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("orders", __name__)


class OrderCreate(BaseModel):
    product_ids: List[str]


class OrderPay(BaseModel):
    payment_method: str


@bp.post("/orders")
@endpoint(body=OrderCreate, auth=True)
def create_order(ctx: EndpointContext):
    try:
        return OrderService(ctx.db).create_order(
            buyer_id=ctx.user_id,
            product_ids=ctx.body.product_ids,
        )
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc


@bp.get("/orders")
@endpoint(auth=True)
def get_orders(ctx: EndpointContext):
    return OrderService(ctx.db).list_orders(
        user_id=ctx.user_id,
        status=ctx.query_str("status"),
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )


@bp.get("/orders/<order_id>")
@endpoint(auth=True)
def get_order(ctx: EndpointContext, order_id: str):
    order = OrderService(ctx.db).get_order(order_id, user_id=ctx.user_id)
    if not order:
        raise ApiError(404, "订单不存在")
    return order


@bp.post("/orders/<order_id>/pay")
@endpoint(body=OrderPay, auth=True)
def pay_order(ctx: EndpointContext, order_id: str):
    try:
        payment_service = PaymentService(ctx.db)
        payment = payment_service.create_payment(order_id, ctx.body.payment_method)
        result = payment_service.process_payment(payment["transaction_id"])
        order = OrderService(ctx.db).get_order(order_id, user_id=ctx.user_id)
        return {"success": result["success"], "message": result["message"], "order": order}
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc


@bp.post("/orders/<order_id>/cancel")
@endpoint(auth=True)
def cancel_order(ctx: EndpointContext, order_id: str):
    service = OrderService(ctx.db)
    try:
        success = service.cancel_order(order_id, ctx.user_id)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    if not success:
        raise ApiError(404, "订单不存在")
    order = service.get_order(order_id, user_id=ctx.user_id)
    return {"message": "订单已取消", "order": order}


@bp.post("/orders/<order_id>/deliver")
@endpoint(auth=True)
def deliver_order(ctx: EndpointContext, order_id: str):
    try:
        order = OrderService(ctx.db).update_order_status(order_id, "delivered")
    except PermissionError as exc:
        raise ApiError(403, str(exc)) from exc
    if not order:
        raise ApiError(404, "订单不存在")
    return {"message": "订单已交付", "order": order}


@bp.post("/orders/<order_id>/complete")
@endpoint(auth=True)
def complete_order(ctx: EndpointContext, order_id: str):
    try:
        order = OrderService(ctx.db).update_order_status(
            order_id,
            "completed",
            user_id=ctx.user_id,
        )
    except PermissionError as exc:
        raise ApiError(403, str(exc)) from exc
    if not order:
        raise ApiError(404, "订单不存在")
    return {"message": "订单已完成", "order": order}


@bp.get("/seller/orders")
@endpoint(auth=True)
def get_seller_orders(ctx: EndpointContext):
    return OrderService(ctx.db).list_orders(
        seller_id=ctx.user_id,
        status=ctx.query_str("status"),
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )
