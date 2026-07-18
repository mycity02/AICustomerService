"""File upload and secure retrieval Flask routes."""
from flask import Blueprint

from services.file_service import FileService
from web import ApiError, BinaryResponse, EndpointContext, endpoint

bp = Blueprint("files", __name__, url_prefix="/files")
file_service = FileService()


@bp.post("/upload")
@endpoint(auth=True, allow_query_token=True)
def upload_file(ctx: EndpointContext):
    uploaded = ctx.file()
    try:
        result = file_service.upload_file(
            uploaded,
            ctx.user_id,
            ctx.form.get("session_id", ""),
        )
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    return {
        "file_id": result["file_id"],
        "file_name": result["file_name"],
        "file_size": result["file_size"],
        "file_type": result["file_type"],
        "upload_url": f"/api/files/{result['file_id']}",
        "extracted_text": result.get("extracted_text"),
        "ocr_used": result.get("ocr_used", False),
        "analysis_pending": result.get("analysis_pending", False),
    }


@bp.get("/<file_id>")
@endpoint(auth=True, allow_query_token=True)
def get_file(ctx: EndpointContext, file_id: str):
    content = file_service.get_file(
        file_id,
        user_id=ctx.user_id,
        session_id=ctx.query_str("session_id"),
    )
    if content is None:
        raise ApiError(404, "file not found")
    return BinaryResponse(content)


@bp.get("/<file_id>/analysis")
@endpoint(auth=True, allow_query_token=True)
def get_file_analysis(ctx: EndpointContext, file_id: str):
    analysis = file_service.get_image_analysis(
        file_id,
        user_id=ctx.user_id,
        session_id=ctx.query_str("session_id"),
    )
    if analysis is None:
        raise ApiError(404, "analysis result not found")
    return analysis
