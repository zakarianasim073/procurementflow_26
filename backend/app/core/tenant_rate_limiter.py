"""Per-tenant rate limiting: Redis-backed token bucket (T-036)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class TenantRateLimiter:
    """Redis-backed per-tenant rate limiter using token bucket algorithm.

    Each tenant gets a bucket that refills with tokens at a fixed rate.
    Requests consume tokens; if bucket is empty, request is rate-limited.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.enabled = redis_client is not None

    def _get_bucket_key(self, tenant_id: str, endpoint: str) -> str:
        """Redis key for rate limit bucket."""
        return f"ratelimit:tenant:{tenant_id}:endpoint:{endpoint}"

    def _get_refill_key(self, tenant_id: str, endpoint: str) -> str:
        """Redis key for last refill timestamp."""
        return f"ratelimit:refill:{tenant_id}:{endpoint}"

    async def get_limits(self, tenant_id: str, plan: str = "free") -> dict:
        """Get rate limits based on tenant plan.

        Plans:
        - free: 100 req/min, 1000 req/hour
        - pro: 500 req/min, 5000 req/hour
        - enterprise: unlimited
        """
        limits = {
            "free": {"per_minute": 100, "per_hour": 1000},
            "pro": {"per_minute": 500, "per_hour": 5000},
            "enterprise": {"per_minute": 10000, "per_hour": 100000},
        }
        return limits.get(plan, limits["free"])

    async def is_allowed(
        self,
        tenant_id: str,
        endpoint: str,
        plan: str = "free",
        per_minute: Optional[int] = None,
    ) -> tuple[bool, Optional[str]]:
        """Check if request is allowed for tenant.

        Returns:
            (allowed, error_message)
        """
        if not self.enabled:
            return True, None

        try:
            limits = await self.get_limits(tenant_id, plan)
            if per_minute is not None:
                limits["per_minute"] = per_minute
            bucket_key = self._get_bucket_key(tenant_id, endpoint)
            refill_key = self._get_refill_key(tenant_id, endpoint)

            # Get current bucket state
            bucket_tokens = await self.redis.get(bucket_key)
            tokens = float(bucket_tokens) if bucket_tokens else limits["per_minute"]

            # Check last refill time
            last_refill = await self.redis.get(refill_key)
            now = datetime.now(timezone.utc).timestamp()

            if last_refill:
                last_refill_ts = float(last_refill)
                elapsed = now - last_refill_ts
                # Refill at 100/60 tokens per second (100 per minute)
                refill_rate = limits["per_minute"] / 60.0
                refill_amount = refill_rate * elapsed
                tokens = min(limits["per_minute"], tokens + refill_amount)
            else:
                # First request
                await self.redis.setex(refill_key, 3600, now)

            # Try to consume one token
            if tokens >= 1:
                tokens -= 1
                await self.redis.setex(bucket_key, 3600, tokens)
                await self.redis.setex(refill_key, 3600, now)
                return True, None
            else:
                return False, f"Rate limited: {endpoint} for {tenant_id} (plan: {plan})"

        except RedisError as e:
            logger.warning(f"Rate limiter error: {e}, allowing request")
            return True, None  # Fail open: allow request if Redis is down

    async def get_status(
        self,
        tenant_id: str,
        endpoint: str,
        plan: str = "free",
    ) -> dict:
        """Get current rate limit status for a tenant/endpoint."""
        if not self.enabled:
            return {"enabled": False, "message": "Redis not available"}

        try:
            limits = await self.get_limits(tenant_id, plan)
            bucket_key = self._get_bucket_key(tenant_id, endpoint)
            bucket_tokens = await self.redis.get(bucket_key)
            tokens = float(bucket_tokens) if bucket_tokens else limits["per_minute"]

            return {
                "enabled": True,
                "tenant_id": tenant_id,
                "endpoint": endpoint,
                "plan": plan,
                "limit_per_minute": limits["per_minute"],
                "current_tokens": round(tokens, 2),
                "tokens_available": round(max(0, tokens), 2),
                "status": "ok" if tokens > 0 else "rate_limited",
            }
        except RedisError as e:
            logger.warning(f"Error getting rate limit status: {e}")
            return {"enabled": False, "error": str(e)}

    async def reset_tenant(self, tenant_id: str) -> bool:
        """Reset all rate limit buckets for a tenant."""
        if not self.enabled:
            return False

        try:
            pattern = f"ratelimit:tenant:{tenant_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            logger.info(f"Reset rate limits for tenant {tenant_id}")
            return True
        except RedisError as e:
            logger.warning(f"Error resetting tenant rate limits: {e}")
            return False


# Global instance (initialized in main.py)
_tenant_rate_limiter: Optional[TenantRateLimiter] = None


def get_tenant_rate_limiter() -> TenantRateLimiter:
    """Get or create tenant rate limiter instance."""
    global _tenant_rate_limiter
    if _tenant_rate_limiter is None:
        _tenant_rate_limiter = TenantRateLimiter()
    return _tenant_rate_limiter


async def init_tenant_rate_limiter(redis_client: redis.Redis) -> TenantRateLimiter:
    """Initialize tenant rate limiter with Redis client."""
    global _tenant_rate_limiter
    _tenant_rate_limiter = TenantRateLimiter(redis_client)
    return _tenant_rate_limiter
