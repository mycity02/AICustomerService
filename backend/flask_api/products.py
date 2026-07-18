"""Product and category Flask routes."""
from typing import List, Optional

from flask import Blueprint
from pydantic import BaseModel

from schemas import UserRole
from services.product_service import CategoryService, ProductService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("products", __name__)


class ProductCreate(BaseModel):
    category_id: str
    title: str
    description: str
    price: float
    original_price: Optional[float] = None
    cover_image: Optional[str] = None
    demo_video: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    difficulty: str = "medium"


class ProductUpdate(BaseModel):
    category_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    cover_image: Optional[str] = None
    demo_video: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    difficulty: Optional[str] = None
    status: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0


def _optional_float(ctx: EndpointContext, name: str) -> float | None:
    raw = ctx.query_str(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ApiError(422, f"query parameter '{name}' must be a number") from exc


@bp.get("/products/categories")
@endpoint(db=True)
def get_categories(ctx: EndpointContext):
    categories = CategoryService(ctx.db).get_categories(
        parent_id=ctx.query_str("parent_id"),
        include_children=ctx.query_bool("include_children"),
    )
    return {"categories": categories}


@bp.get("/products/categories/<category_id>")
@endpoint(db=True)
def get_category(ctx: EndpointContext, category_id: str):
    category = CategoryService(ctx.db).get_category(category_id)
    if not category:
        raise ApiError(404, "分类不存在")
    return category


@bp.post("/products/categories")
@endpoint(body=CategoryCreate, admin=True)
def create_category(ctx: EndpointContext):
    try:
        category = CategoryService(ctx.db).create_category(**ctx.body.model_dump())
        return {"message": "分类创建成功", "category_id": category.id}
    except Exception as exc:
        raise ApiError(400, str(exc)) from exc


@bp.get("/products")
@endpoint(db=True)
def get_products(ctx: EndpointContext):
    return ProductService(ctx.db).search_products(
        keyword=ctx.query_str("keyword"),
        category_id=ctx.query_str("category_id"),
        min_price=_optional_float(ctx, "min_price"),
        max_price=_optional_float(ctx, "max_price"),
        difficulty=ctx.query_str("difficulty"),
        status=ctx.query_str("status"),
        sort_by=ctx.query_str("sort_by", "created_at"),
        order=ctx.query_str("order", "desc"),
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )


@bp.get("/products/<product_id>")
@endpoint(db=True)
def get_product(ctx: EndpointContext, product_id: str):
    product = ProductService(ctx.db).get_product(product_id, increment_view=True)
    if not product:
        raise ApiError(404, "商品不存在")
    return product


@bp.post("/products")
@endpoint(body=ProductCreate, auth=True)
def create_product(ctx: EndpointContext):
    try:
        product = ProductService(ctx.db).create_product(
            seller_id=ctx.user_id,
            **ctx.body.model_dump(),
        )
        return {"message": "商品创建成功", "product_id": product.id}
    except Exception as exc:
        raise ApiError(400, str(exc)) from exc


def _can_manage_product(ctx: EndpointContext, product: dict) -> bool:
    return product["seller"]["id"] == ctx.user_id or ctx.user.role == UserRole.ADMIN


@bp.put("/products/<product_id>")
@endpoint(body=ProductUpdate, auth=True)
def update_product(ctx: EndpointContext, product_id: str):
    service = ProductService(ctx.db)
    product = service.get_product(product_id)
    if not product:
        raise ApiError(404, "商品不存在")
    if not _can_manage_product(ctx, product):
        raise ApiError(403, "无权操作此商品")
    try:
        updated = service.update_product(
            product_id,
            **ctx.body.model_dump(exclude_none=True),
        )
    except Exception as exc:
        raise ApiError(400, str(exc)) from exc
    if not updated:
        raise ApiError(404, "商品不存在")
    return {"message": "商品更新成功", "product_id": updated.id}


@bp.delete("/products/<product_id>")
@endpoint(auth=True)
def delete_product(ctx: EndpointContext, product_id: str):
    service = ProductService(ctx.db)
    product = service.get_product(product_id)
    if not product:
        raise ApiError(404, "商品不存在")
    if not _can_manage_product(ctx, product):
        raise ApiError(403, "无权操作此商品")
    try:
        success = service.delete_product(product_id)
    except Exception as exc:
        raise ApiError(400, str(exc)) from exc
    if not success:
        raise ApiError(404, "商品不存在")
    return {"message": "商品删除成功"}


@bp.get("/products/<product_id>/seller")
@endpoint(db=True)
def get_seller_products(ctx: EndpointContext, product_id: str):
    # Preserve the historical route while treating the path value as seller id.
    return ProductService(ctx.db).search_products(
        seller_id=product_id,
        status="published",
        page=ctx.query_int("page", 1, minimum=1),
        page_size=ctx.query_int("page_size", 20, minimum=1, maximum=100),
    )
