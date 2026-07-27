"""
In-memory rate limiting middleware for FastAPI.
Uses a sliding window per client IP + optional API key.
Production should replace with Redis-backed limiter.
"""
import time
import logging
from collections import defaultdict
from threading import Lock
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.tenant_rate_limiter import get_tenant_rate_limiter

logger = logging.getLogger("procureflow.rate_limiter")

# Default: 100 requests per 60 seconds per client
DEFAULT_RATE = 100
DEFAULT_WINDOW = 60

# Per-path overrides (higher limits for common endpoints)
PATH_LIMITS = {
    "/api/health": (300, 60),
    "/api/ready": (300, 60),
    "/api/live": (300, 60),
    "/api/v1/contractors": (50, 60),
    "/api/v1/search": (30, 60),
}


class InMemoryRateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self, max_requests: int = DEFAULT_RATE, window_secs: int = DEFAULT_WINDOW):
        self.max_requests = max_requests
        self.window_secs = window_secs
        self._clients: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _clean_window(self, client_id: str, now: float, window_secs: int) -> None:
        cutoff = now - window_secs
        self._clients[client_id] = [t for t in self._clients[client_id] if t > cutoff]

    def is_allowed(
        self,
        client_id: str,
        max_requests: int | None = None,
        window_secs: int | None = None,
    ) -> tuple[bool, int, int]:
        """Return (allowed, remaining, reset_seconds)."""
        max_requests = max_requests or self.max_requests
        window_secs = window_secs or self.window_secs
        now = time.time()
        with self._lock:
            self._clean_window(client_id, now, window_secs)
            count = len(self._clients[client_id])
            if count >= max_requests:
                oldest = min(self._clients[client_id]) if self._clients[client_id] else now
                reset_secs = int(oldest + window_secs - now) + 1
                return False, 0, reset_secs
            self._clients[client_id].append(now)
            remaining = max_requests - count - 1
            return True, remaining, window_secs

    def get_limit_for_path(self, path: str) -> tuple[int, int]:
        """Return (max_requests, window_secs) for a path."""
        for prefix, (limit, window) in PATH_LIMITS.items():
            if path.startswith(prefix):
                return limit, window
        return self.max_requests, self.window_secs


# Singleton
_limiter: InMemoryRateLimiter | None = None


def get_rate_limiter() -> InMemoryRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = InMemoryRateLimiter()
    return _limiter


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware: rate-limit by client IP + optional API key."""
    # Skip non-API paths
    if not request.url.path.startswith("/api"):
        return await call_next(request)

    # Skip OPTIONS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    limiter = get_rate_limiter()
    client_ip = request.client.host if request.client else "unknown"
    user = getattr(request.state, "user", None) or {}
    tenant_id = user.get("tenant_id")
    client_id = str(tenant_id) if tenant_id else f"ip:{client_ip}"
    limit, window = limiter.get_limit_for_path(request.url.path)
    endpoint = next(
        (prefix for prefix in PATH_LIMITS if request.url.path.startswith(prefix)),
        "/" + "/".join(request.url.path.strip("/").split("/")[:3]),
    )

    distributed = get_tenant_rate_limiter()
    if distributed.enabled:
        allowed, _ = await distributed.is_allowed(
            client_id,
            endpoint,
            user.get("plan", "free"),
            per_minute=limit,
        )
        remaining = -1
        reset_secs = window
    else:
        allowed, remaining, reset_secs = limiter.is_allowed(
            f"{client_id}:{endpoint}",
            max_requests=limit,
            window_secs=window,
        )

    if not allowed:
        logger.warning("Rate limit hit for client=%s path=%s", client_id[:40], request.url.path)
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please try again later.",
                "retry_after_seconds": reset_secs,
            },
            headers={
                "Retry-After": str(reset_secs),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_secs),
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_secs)
    return response
