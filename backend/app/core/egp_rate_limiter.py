"""e-GP distributed rate limiter, backoff, and circuit breaker (T-019/AGT-02).

Provides Redis-backed rate limiting (token bucket), exponential backoff with jitter,
and circuit breaker for coordinated e-GP crawl control across processes.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Rate limit exceeded; client should back off."""
    pass


class CircuitBreakerOpen(Exception):
    """Circuit breaker is open; service temporarily unavailable."""
    pass


class RedisTokenBucket:
    """Token bucket rate limiter using Redis as a distributed state store.

    Allows burst traffic up to `burst` tokens, refilling at `rate` tokens/second.
    """

    def __init__(self, redis_client, key: str, rate: float, burst: int):
        """Initialize token bucket.

        Args:
            redis_client: Redis async client (redis.asyncio)
            key: Redis key for this bucket (e.g., "pf:egp:rate")
            rate: Tokens per second (refill rate)
            burst: Maximum burst size (bucket capacity)
        """
        self.redis = redis_client
        self.key = key
        self.rate = rate
        self.burst = burst
        self.last_refill_key = f"{key}:last_refill"

    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket.

        Returns True if acquired, False if would exceed rate limit.
        """
        if not self.redis:
            return True

        try:
            pipe = self.redis.pipeline()
            pipe.get(self.key)
            pipe.get(self.last_refill_key)
            results = await pipe.execute()

            current_tokens = float(results[0] or self.burst)
            last_refill = float(results[1] or time.time())
            now = time.time()

            # Refill tokens based on elapsed time
            elapsed = now - last_refill
            refilled = min(self.burst, current_tokens + elapsed * self.rate)

            # Try to acquire
            if refilled >= tokens:
                new_tokens = refilled - tokens
                pipe = self.redis.pipeline()
                pipe.set(self.key, str(new_tokens), ex=3600)
                pipe.set(self.last_refill_key, str(now), ex=3600)
                await pipe.execute()
                return True
            else:
                # Not enough tokens; update refill time for next caller
                await self.redis.set(self.last_refill_key, str(now), ex=3600)
                return False
        except Exception as e:
            logger.warning(f"Token bucket check failed: {e}; allowing request")
            return True  # Fail open on Redis error


class ExponentialBackoff:
    """Exponential backoff with jitter for retry logic."""

    def __init__(self, base: float = 1.0, max_retries: int = 3, jitter: bool = True):
        """Initialize backoff.

        Args:
            base: Initial backoff in seconds
            max_retries: Maximum retry attempts
            jitter: Add random jitter to backoff
        """
        self.base = base
        self.max_retries = max_retries
        self.jitter = jitter
        self.attempt = 0

    def next_delay(self) -> float:
        """Get next backoff delay and increment attempt."""
        if self.attempt >= self.max_retries:
            raise RuntimeError(f"Max retries ({self.max_retries}) exceeded")

        delay = self.base * (2 ** self.attempt)
        if self.jitter:
            delay *= 0.5 + random.random()

        self.attempt += 1
        return delay

    async def sleep_and_retry(self) -> None:
        """Sleep for next backoff duration."""
        delay = self.next_delay()
        logger.debug(f"Backoff attempt {self.attempt}: sleeping {delay:.2f}s")
        await asyncio.sleep(delay)

    def reset(self) -> None:
        """Reset attempt counter."""
        self.attempt = 0


class CircuitBreaker:
    """Circuit breaker pattern for e-GP service (using Redis for distributed state)."""

    def __init__(
        self,
        redis_client,
        key: str = "pf:egp:circuit",
        failure_threshold: int = 5,
        cool_down_seconds: int = 300,
    ):
        """Initialize circuit breaker.

        Args:
            redis_client: Redis async client (redis.asyncio)
            key: Redis key for breaker state
            failure_threshold: Failures before opening circuit
            cool_down_seconds: Duration circuit stays open
        """
        self.redis = redis_client
        self.key = key
        self.failure_count_key = f"{key}:failures"
        self.opened_at_key = f"{key}:opened_at"
        self.failure_threshold = failure_threshold
        self.cool_down = cool_down_seconds

    async def is_open(self) -> bool:
        """Check if circuit is currently open."""
        if not self.redis:
            return False

        try:
            opened_at = await self.redis.get(self.opened_at_key)
            if not opened_at:
                return False
            elapsed = time.time() - float(opened_at)
            return elapsed < self.cool_down
        except Exception as e:
            logger.warning(f"Circuit breaker check failed: {e}; allowing request")
            return False

    async def record_success(self) -> None:
        """Record successful call; reset failure count."""
        if not self.redis:
            return

        try:
            await self.redis.delete(self.failure_count_key, self.opened_at_key)
            logger.info("Circuit breaker: success; failures reset")
        except Exception as e:
            logger.warning(f"Could not record success: {e}")

    async def record_failure(self) -> None:
        """Record failure; open circuit if threshold exceeded."""
        if not self.redis:
            return

        try:
            failures = await self.redis.incr(self.failure_count_key)
            if failures >= self.failure_threshold:
                await self.redis.set(self.opened_at_key, str(time.time()), ex=self.cool_down)
                logger.error(
                    f"Circuit breaker: OPEN after {failures} consecutive failures "
                    f"(cool-down {self.cool_down}s)"
                )
            else:
                logger.warning(f"Circuit breaker: failure {failures}/{self.failure_threshold}")
        except Exception as e:
            logger.warning(f"Could not record failure: {e}")
