"""Favorites Flask routes."""
from flask import Blueprint
from pydantic import BaseModel

from services.favorite_service import FavoriteService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("favorites", __name__)


class FavoriteAdd(BaseModel):
    product_id: str


@bp.post("/favorites")
@endpoint(body=FavoriteAdd, auth=True)
def add_favorite(ctx: EndpointContext):
    try:
        return FavoriteService(ctx.db).add_favorite(ctx.user_id, ctx.body.product_id)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc


@bp.get("/favorites")
@endpoint(auth=True)
def get_favorites(ctx: EndpointContext):
    return FavoriteService(ctx.db).get_favorites(
        user_id=ctx.user_id,
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )


@bp.delete("/favorites/<product_id>")
@endpoint(auth=True)
def remove_favorite(ctx: EndpointContext, product_id: str):
    if not FavoriteService(ctx.db).remove_favorite(ctx.user_id, product_id):
        raise ApiError(404, "未收藏此商品")
    return {"message": "取消收藏成功"}


@bp.get("/favorites/<product_id>/check")
@endpoint(auth=True)
def check_favorite(ctx: EndpointContext, product_id: str):
    value = FavoriteService(ctx.db).is_favorited(ctx.user_id, product_id)
    return {"is_favorited": value}
