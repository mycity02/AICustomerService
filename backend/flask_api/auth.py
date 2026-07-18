"""Authentication Flask routes."""
from flask import Blueprint

from schemas import TokenRefresh, UserCreate, UserLogin
from services.auth_service import AuthService
from web import ApiError, EndpointContext, endpoint

bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_service = AuthService()


@bp.post("/register")
@endpoint(body=UserCreate, db=True)
def register(ctx: EndpointContext):
    try:
        return auth_service.register(ctx.db, ctx.body)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc


@bp.post("/login")
@endpoint(body=UserLogin, db=True)
def login(ctx: EndpointContext):
    try:
        return auth_service.login(ctx.db, ctx.body)
    except ValueError as exc:
        raise ApiError(401, str(exc)) from exc


@bp.post("/refresh")
@endpoint(body=TokenRefresh)
def refresh_token(ctx: EndpointContext):
    try:
        return auth_service.refresh_access_token(ctx.body.refresh_token)
    except ValueError as exc:
        raise ApiError(401, str(exc)) from exc


@bp.post("/logout")
@endpoint(auth=True)
def logout(ctx: EndpointContext):
    return {"message": "登出成功"}


@bp.get("/me")
@endpoint(auth=True)
def get_current_user_info(ctx: EndpointContext):
    return ctx.user
