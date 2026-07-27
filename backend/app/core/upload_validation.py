"""
File upload validation middleware for FastAPI.
Enforces file size limits and MIME type allowlists for all upload endpoints.

Rejection contract (T-006 / SEC-05):
- 413 {"detail": "File too large", "errors": [...]} for oversize uploads
- 415 {"detail": "Unsupported file type", "errors": [...]} for disallowed types
- 400 {"detail": "Invalid form data"} for unparseable multipart bodies
"""
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("procureflow.upload_validation")

# Max file size (bytes) — overridable via env var
MAX_FILE_SIZE = int(os.getenv("UPLOAD_MAX_SIZE_MB", "50")) * 1024 * 1024
# Multipart framing overhead allowance for the whole-request Content-Length check
_MULTIPART_OVERHEAD = 1024 * 1024

# Allowlisted extensions per category
ALLOWED_DOCUMENTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".json"}
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

UPLOAD_PATHS = {"/api/boq/upload", "/api/v1/tender-docs/generate", "/api/v1/sor/upload",
                "/api/v1/rate-analysis/upload", "/api/boq/upload-compare"}


def _reject(status_code: int, detail: str, errors: list[str]) -> JSONResponse:
    logger.warning("Upload validation failed (%d): %s", status_code, errors)
    return JSONResponse(status_code=status_code, content={"detail": detail, "errors": errors})


async def upload_validation_middleware(request: Request, call_next):
    """Validate file uploads before they reach the route handler."""
    if request.method not in {"POST", "PUT", "PATCH"}:
        return await call_next(request)
    if request.url.path.rstrip("/") not in UPLOAD_PATHS:
        return await call_next(request)

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return await call_next(request)

    # Cheap early rejection: whole-request Content-Length already exceeds the
    # cap — no point parsing the multipart body.
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > MAX_FILE_SIZE + _MULTIPART_OVERHEAD:
            return _reject(413, "File too large", [
                f"request body {int(content_length) // (1024 * 1024)}MB exceeds "
                f"max size of {MAX_FILE_SIZE // (1024 * 1024)}MB"
            ])

    # Cache the raw body BEFORE parsing the form: request.body() stores it on
    # the request so Starlette's middleware stack replays it to the route
    # handler. Parsing the form without this consumes the stream and the
    # endpoint receives an empty body (422).
    try:
        await request.body()
        form = await request.form()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid form data"})

    size_errors: list[str] = []
    type_errors: list[str] = []
    for field_name, field_value in form.items():
        if not hasattr(field_value, "filename"):
            continue
        filename = getattr(field_value, "filename", "") or ""
        ext = (os.path.splitext(filename)[1] or "").lower()

        # Validate file size
        size = getattr(field_value, "size", None)
        if size and size > MAX_FILE_SIZE:
            size_errors.append(f"{filename}: exceeds max size of {MAX_FILE_SIZE // (1024 * 1024)}MB")

        # Validate extension
        if ext and ext not in (ALLOWED_DOCUMENTS | ALLOWED_IMAGES):
            type_errors.append(f"{filename}: file type '{ext}' not allowed")
        elif not ext:
            type_errors.append(f"{filename}: missing file extension")

    if size_errors:
        return _reject(413, "File too large", size_errors)
    if type_errors:
        return _reject(415, "Unsupported file type", type_errors)

    # Re-inject form data as request.state (already consumed by request.form())
    request.state.validated_form = form
    return await call_next(request)
