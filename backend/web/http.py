"""Reusable synchronous Flask endpoint, validation, auth, and response helpers."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Mapping, TypeVar

from flask import Response, current_app, jsonify, request, stream_with_context
from pydantic import BaseModel, ValidationError
from sqlalchemy.inspection import inspect as sqlalchemy_inspect
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException

from database import db_session
from schemas import UserRole
from services.auth_service import AuthService


logger = logging.getLogger(__name__)
auth_service = AuthService()
F = TypeVar("F", bound=Callable[..., Any])


class ApiError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class UploadedFile:
    """Small synchronous facade over Werkzeug's uploaded file object."""

    def __init__(self, storage: FileStorage):
        self._storage = storage
        self.filename = storage.filename or ""
        self.content_type = storage.content_type
        self.file = storage.stream

    def read(self, size: int = -1) -> bytes:
        return self._storage.read(size)


@dataclass
class BinaryResponse:
    content: bytes
    mimetype: str = "application/octet-stream"
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass
class SSEStream:
    events: Any


@dataclass
class EndpointContext:
    body: Any = None
    json: Any = None
    query: dict[str, str] = field(default_factory=dict)
    query_lists: dict[str, list[str]] = field(default_factory=dict)
    form: dict[str, str] = field(default_factory=dict)
    files: dict[str, UploadedFile] = field(default_factory=dict)
    token: str | None = None
    db: Any = None
    user: Any = None

    @property
    def user_id(self) -> str:
        if self.user is None:
            raise ApiError(401, "authentication required")
        return self.user.id

    def query_str(self, name: str, default: str | None = None) -> str | None:
        value = self.query.get(name)
        return default if value in (None, "") else value

    def query_int(
        self,
        name: str,
        default: int,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        raw = self.query.get(name)
        try:
            value = default if raw in (None, "") else int(raw)
        except (TypeError, ValueError) as exc:
            raise ApiError(422, f"query parameter '{name}' must be an integer") from exc
        if minimum is not None and value < minimum:
            raise ApiError(422, f"query parameter '{name}' must be >= {minimum}")
        if maximum is not None and value > maximum:
            raise ApiError(422, f"query parameter '{name}' must be <= {maximum}")
        return value

    def query_bool(self, name: str, default: bool = False) -> bool:
        raw = self.query.get(name)
        if raw in (None, ""):
            return default
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ApiError(422, f"query parameter '{name}' must be a boolean")

    def file(self, name: str = "file", *, required: bool = True) -> UploadedFile | None:
        uploaded = self.files.get(name)
        if required and uploaded is None:
            raise ApiError(422, f"missing uploaded file '{name}'")
        return uploaded


def _extract_bearer_token(*, allow_query_token: bool) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    if allow_query_token:
        token = request.args.get("token", "").strip()
        if token:
            return token
    return None


def _snapshot_request(body_model: type[BaseModel] | None, *, allow_query_token: bool) -> EndpointContext:
    payload = request.get_json(silent=True) if request.is_json else None
    body = body_model.model_validate(payload or {}) if body_model else None
    return EndpointContext(
        body=body,
        json=payload,
        query=request.args.to_dict(flat=True),
        query_lists={key: request.args.getlist(key) for key in request.args.keys()},
        form=request.form.to_dict(flat=True),
        files={key: UploadedFile(value) for key, value in request.files.items()},
        token=_extract_bearer_token(allow_query_token=allow_query_token),
    )


def _invoke_with_context(
    func: Callable[..., Any],
    context: EndpointContext,
    path_values: dict[str, Any],
    *,
    use_db: bool,
    require_auth: bool,
    require_admin: bool,
) -> Any:
    def invoke() -> Any:
        if require_auth:
            if not context.token:
                raise ApiError(401, "missing authentication token")
            try:
                context.user = auth_service.get_current_user(context.db, context.token)
            except ValueError as exc:
                raise ApiError(401, str(exc)) from exc
            if require_admin and context.user.role != UserRole.ADMIN:
                raise ApiError(403, "需要管理员权限")
        return func(context, **path_values)

    if not use_db:
        return invoke()

    with db_session() as session:
        context.db = session
        try:
            result = invoke()
            session.commit()
            return result
        except BaseException:
            session.rollback()
            raise


def endpoint(
    *,
    body: type[BaseModel] | None = None,
    db: bool = False,
    auth: bool = False,
    admin: bool = False,
    allow_query_token: bool = False,
    status_code: int = 200,
) -> Callable[[F], F]:
    """Turn a synchronous business handler into a Flask view."""
    use_db = db or auth or admin
    require_auth = auth or admin

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(**path_values: Any):
            context = _snapshot_request(body, allow_query_token=allow_query_token)
            result = _invoke_with_context(
                func,
                context,
                path_values,
                use_db=use_db,
                require_auth=require_auth,
                require_admin=admin,
            )
            return make_response(result, status_code=status_code)

        return wrapper  # type: ignore[return-value]

    return decorator


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    try:
        mapper = sqlalchemy_inspect(value.__class__)
        return {column.key: _jsonable(getattr(value, column.key)) for column in mapper.columns}
    except Exception:
        return str(value)


def _sse_response(stream: SSEStream) -> Response:
    @stream_with_context
    def generate():
        try:
            for event in stream.events:
                yield f"data: {json.dumps(_jsonable(event), ensure_ascii=False)}\n\n"
        except GeneratorExit:
            logger.info("SSE client disconnected")
        except Exception:
            logger.exception("SSE stream failed")
            yield 'data: {"type":"error","message":"stream processing failed"}\n\n'
            yield 'data: {"type":"end","status":"error"}\n\n'

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache, no-store"
    response.headers["X-Accel-Buffering"] = "no"
    return response

def make_response(value: Any, *, status_code: int = 200):
    if isinstance(value, Response):
        return value
    if isinstance(value, BinaryResponse):
        response = Response(value.content, status=status_code, mimetype=value.mimetype)
        response.headers.update(value.headers)
        return response
    if isinstance(value, SSEStream):
        return _sse_response(value)
    return jsonify(_jsonable(value)), status_code


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"detail": _jsonable(error.detail)}), error.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return jsonify({"detail": error.errors(include_url=False)}), 422

    @app.errorhandler(WerkzeugHTTPException)
    def handle_http_error(error: WerkzeugHTTPException):
        return jsonify({"detail": error.description}), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        current_app.logger.exception("Unhandled request error", exc_info=error)
        return jsonify({"detail": "internal server error"}), 500
