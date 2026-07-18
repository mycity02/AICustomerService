"""Product review Flask routes."""
from typing import List, Optional

from flask import Blueprint
from pydantic import BaseModel

from services.review_service import ReviewService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("reviews", __name__)


class ReviewCreate(BaseModel):
    order_item_id: str
    rating: int
    content: Optional[str] = None
    images: Optional[List[str]] = None


class ReviewReply(BaseModel):
    reply: str


@bp.post("/reviews")
@endpoint(body=ReviewCreate, auth=True)
def create_review(ctx: EndpointContext):
    try:
        return ReviewService(ctx.db).create_review(
            order_item_id=ctx.body.order_item_id,
            buyer_id=ctx.user_id,
            rating=ctx.body.rating,
            content=ctx.body.content,
            images=ctx.body.images,
        )
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    except PermissionError as exc:
        raise ApiError(403, str(exc)) from exc


@bp.get("/reviews")
@endpoint(db=True)
def get_reviews(ctx: EndpointContext):
    return ReviewService(ctx.db).get_reviews(
        product_id=ctx.query_str("product_id"),
        buyer_id=ctx.query_str("buyer_id"),
        seller_id=ctx.query_str("seller_id"),
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )


@bp.post("/reviews/<review_id>/reply")
@endpoint(body=ReviewReply, auth=True)
def reply_review(ctx: EndpointContext, review_id: str):
    try:
        return ReviewService(ctx.db).reply_review(
            review_id=review_id,
            seller_id=ctx.user_id,
            reply=ctx.body.reply,
        )
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    except PermissionError as exc:
        raise ApiError(403, str(exc)) from exc


@bp.get("/products/<product_id>/reviews")
@endpoint(db=True)
def get_product_reviews(ctx: EndpointContext, product_id: str):
    return ReviewService(ctx.db).get_reviews(
        product_id=product_id,
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )
