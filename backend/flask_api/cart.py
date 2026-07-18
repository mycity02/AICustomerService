"""Shopping cart Flask routes."""
from flask import Blueprint
from pydantic import BaseModel

from services.cart_service import CartService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("cart", __name__)


class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


@bp.get("/cart")
@endpoint(auth=True)
def get_cart(ctx: EndpointContext):
    return CartService(ctx.db).get_cart(ctx.user_id)


@bp.post("/cart")
@endpoint(body=CartItemAdd, auth=True)
def add_to_cart(ctx: EndpointContext):
    try:
        return CartService(ctx.db).add_to_cart(ctx.user_id, ctx.body.product_id, ctx.body.quantity)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc


@bp.put("/cart/<product_id>")
@endpoint(body=CartItemUpdate, auth=True)
def update_cart_item(ctx: EndpointContext, product_id: str):
    try:
        result = CartService(ctx.db).update_quantity(ctx.user_id, product_id, ctx.body.quantity)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    if not result:
        raise ApiError(404, "购物车中没有此商品")
    return result


@bp.delete("/cart/<product_id>")
@endpoint(auth=True)
def remove_from_cart(ctx: EndpointContext, product_id: str):
    if not CartService(ctx.db).remove_from_cart(ctx.user_id, product_id):
        raise ApiError(404, "购物车中没有此商品")
    return {"message": "删除成功"}


@bp.delete("/cart")
@endpoint(auth=True)
def clear_cart(ctx: EndpointContext):
    CartService(ctx.db).clear_cart(ctx.user_id)
    return {"message": "购物车已清空"}


@bp.get("/cart/count")
@endpoint(auth=True)
def get_cart_count(ctx: EndpointContext):
    return {"count": CartService(ctx.db).get_cart_count(ctx.user_id)}
