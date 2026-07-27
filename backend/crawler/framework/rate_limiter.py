from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional

from .config import settings
from .logger import get_logger
from .metrics import record_error

log = get_logger("crawler.rate_limiter")


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0) -> float:
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return 0.0
        needed = tokens - self._tokens
        wait = needed / self._rate
        await asyncio.sleep(wait)
        self._tokens = 0.0
        self._last_refill = time.monotonic()
        return wait


class AdaptiveRateLimiter:
    def __init__(self, base_rate: float = 0.5, burst: int = 2):
        self._base_rate = base_rate
        self._burst = burst
        self._bucket = TokenBucket(base_rate, burst)
        self._domain_buckets: Dict[str, TokenBucket] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._consecutive_errors: int = 0
        self._consecutive_success: int = 0
        self._current_rate: float = base_rate

    async def acquire(self, domain: str = "") -> float:
        if settings.rate_limit_per_domain and domain:
            async with self._lock:
                if domain not in self._domain_buckets:
                    self._domain_buckets[domain] = TokenBucket(
                        self._base_rate, self._burst
                    )
                bucket = self._domain_buckets[domain]
        else:
            bucket = self._bucket
        wait = await bucket.acquire()
        if wait > 0.1:
            log.debug("rate_limited", domain=domain or "global", wait_s=round(wait, 2))
        return wait

    def record_success(self):
        self._consecutive_success += 1
        self._consecutive_errors = 0
        if self._consecutive_success > 10 and self._current_rate < 2.0:
            self._current_rate = min(2.0, self._current_rate * 1.1)
            self._bucket = TokenBucket(self._current_rate, self._burst)

    def record_error(self):
        self._consecutive_errors += 1
        self._consecutive_success = 0
        if self._consecutive_errors >= 3:
            self._current_rate = max(0.1, self._current_rate * 0.5)
            self._bucket = TokenBucket(self._current_rate, self._burst)
            log.warning("rate_limiter_backoff", rate=self._current_rate)

    def reset(self):
        self._current_rate = self._base_rate
        self._bucket = TokenBucket(self._base_rate, self._burst)
        self._consecutive_errors = 0
        self._consecutive_success = 0

    @property
    def rate(self) -> float:
        return self._current_rate


_rate_limiter: Optional[AdaptiveRateLimiter] = None


def get_rate_limiter() -> AdaptiveRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AdaptiveRateLimiter(
            base_rate=settings.rate_limit_min_s,
            burst=max(2, int(settings.rate_limit_max_s / settings.rate_limit_min_s)),
        )
    return _rate_limiter
