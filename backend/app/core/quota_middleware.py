"""Quota enforcement middleware: check before mutations (T-036)."""

from __future__ import annotations

import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.quota_service import QuotaService
from app.db.database import get_async_session

logger = logging.getLogger(__name__)

# Endpoints that consume tender quota (mutations only)
QUOTA_CONSUMING_ENDPOINTS = {
    ("/api/tenders", "POST"),
    ("/api/tender", "POST"),
    ("/api/v1/tender", "POST"),
    ("/api/boq", "POST"),
    ("/api/v1/boq", "POST"),
    ("/api/boq/compare", "POST"),
    ("/api/agents", "POST"),
    ("/api/v1/agents", "POST"),
}


class QuotaEnforcementMiddleware(BaseHTTPMiddleware):
    """Check tenant quota before allowing mutations."""

    async def dispatch(self, request: Request, call_next):
        """Check quota for mutation endpoints."""
        # Only check on mutations
        if request.method not in {"POST", "PUT", "DELETE"}:
            return await call_next(request)

        # Only check on tenant-scoped endpoints
        path = request.url.path
        method = request.method
        is_quota_endpoint = any(
            path.startswith(prefix) for prefix, m in QUOTA_CONSUMING_ENDPOINTS if m == method
        )

        if not is_quota_endpoint:
            return await call_next(request)

        # Get tenant context from request state
        tenant_id = getattr(request.state, "tenant_id", None)
        user = getattr(request.state, "user", None)

        if not tenant_id or not user:
            # Not authenticated or no tenant context
            return await call_next(request)

        # Check quota
        try:
            async with get_async_session() as db:
                has_quota, error = await QuotaService.check_tender_quota(db, tenant_id)

                if not has_quota:
                    logger.warning(
                        "Quota exhausted: user=%s tenant=%s endpoint=%s",
                        user.get("id") if isinstance(user, dict) else getattr(user, "id", None),
                        tenant_id,
                        path,
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "quota_exhausted",
                            "message": error or "Tender quota exhausted for this month",
                            "status_code": 429,
                        },
                    )
        except Exception as e:
            logger.warning(f"Quota check error: {e}, allowing request")
            # Fail open: if quota check fails, allow request

        # Call the next handler
        return await call_next(request)
