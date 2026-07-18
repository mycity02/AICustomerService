"""Browse history and recommendation Flask routes."""
from flask import Blueprint
from pydantic import BaseModel

from services.browse_service import BrowseService
from services.recommendation_service import RecommendationService
from web import EndpointContext, endpoint

bp = Blueprint("browse", __name__)


class BrowseRecord(BaseModel):
    product_id: str
    view_duration: int = 0


@bp.get("/recommendations")
@endpoint(auth=True)
def get_personalized_recommendations(ctx: EndpointContext):
    exclude_ids = ctx.query_str("exclude_ids")
    excluded = [item.strip() for item in exclude_ids.split(",") if item.strip()] if exclude_ids else []
    recommendations = RecommendationService(ctx.db).get_personalized_recommendations(
        user_id=ctx.user_id,
        limit=ctx.query_int("limit", 10, minimum=1, maximum=20),
        exclude_ids=excluded,
    )
    return {"recommendations": recommendations}


@bp.get("/recommendations/similar/<product_id>")
@endpoint(db=True)
def get_similar_products(ctx: EndpointContext, product_id: str):
    similar = RecommendationService(ctx.db).get_similar_products(
        product_id=product_id,
        limit=ctx.query_int("limit", 5, minimum=1, maximum=20),
    )
    return {"similar_products": similar}


@bp.post("/browse")
@endpoint(body=BrowseRecord, auth=True)
def record_browse(ctx: EndpointContext):
    return BrowseService(ctx.db).record_browse(
        user_id=ctx.user_id,
        product_id=ctx.body.product_id,
        view_duration=ctx.body.view_duration,
    )


@bp.get("/browse")
@endpoint(auth=True)
def get_browse_history(ctx: EndpointContext):
    return BrowseService(ctx.db).get_browse_history(
        user_id=ctx.user_id,
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )


@bp.get("/browse/interests")
@endpoint(auth=True)
def get_user_interests(ctx: EndpointContext):
    return BrowseService(ctx.db).get_user_interests(user_id=ctx.user_id)


@bp.delete("/browse/<product_id>")
@endpoint(auth=True)
def delete_browse_record(ctx: EndpointContext, product_id: str):
    BrowseService(ctx.db).delete_browse_record(user_id=ctx.user_id, product_id=product_id)
    return {"message": "删除成功"}


@bp.delete("/browse")
@endpoint(auth=True)
def clear_browse_history(ctx: EndpointContext):
    BrowseService(ctx.db).clear_browse_history(user_id=ctx.user_id)
    return {"message": "清空成功"}
