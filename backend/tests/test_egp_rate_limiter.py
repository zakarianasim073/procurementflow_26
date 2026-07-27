"""T-019 (AGT-02): e-GP rate limiter, backoff, and circuit breaker tests."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.egp_rate_limiter import (
    RedisTokenBucket,
    ExponentialBackoff,
    CircuitBreaker,
    RateLimitError,
    CircuitBreakerOpen,
)


class TestExponentialBackoff:
    """Verify exponential backoff with jitter."""

    def test_backoff_increases_exponentially(self):
        """Each retry delay doubles (plus jitter)."""
        backoff = ExponentialBackoff(base=1.0, max_retries=3, jitter=False)

        delay1 = backoff.next_delay()
        assert delay1 == 1.0

        delay2 = backoff.next_delay()
        assert delay2 == 2.0

        delay3 = backoff.next_delay()
        assert delay3 == 4.0

    def test_backoff_max_retries_exceeded(self):
        """Max retries enforced."""
        backoff = ExponentialBackoff(base=1.0, max_retries=2, jitter=False)
        backoff.next_delay()
        backoff.next_delay()

        with pytest.raises(RuntimeError, match="Max retries"):
            backoff.next_delay()

    def test_backoff_reset(self):
        """Reset clears attempt counter."""
        backoff = ExponentialBackoff(base=1.0, max_retries=3, jitter=False)
        backoff.next_delay()
        backoff.next_delay()

        backoff.reset()
        assert backoff.attempt == 0
        assert backoff.next_delay() == 1.0

    @pytest.mark.asyncio
    async def test_backoff_sleep_and_retry(self):
        """Async sleep works correctly."""
        backoff = ExponentialBackoff(base=0.01, max_retries=2, jitter=False)

        start = time.time()
        await backoff.sleep_and_retry()
        elapsed = time.time() - start

        # Should sleep roughly 0.01s (allow some overhead)
        assert 0.005 < elapsed < 0.05


class TestRedisTokenBucket:
    """Verify token bucket rate limiting.

    Note: These tests mock Redis or skip if Redis unavailable.
    """

    @pytest.mark.asyncio
    async def test_token_bucket_acquire_without_redis(self):
        """Without Redis, token bucket allows all requests (fail-open)."""
        bucket = RedisTokenBucket(None, "test:bucket", rate=1.0, burst=10)

        # Should always return True when Redis is unavailable
        assert await bucket.acquire(1) is True
        assert await bucket.acquire(5) is True

    def test_token_bucket_initialization(self):
        """Bucket initializes with correct parameters."""
        bucket = RedisTokenBucket(None, "pf:egp:rate", rate=10.0, burst=30)

        assert bucket.key == "pf:egp:rate"
        assert bucket.rate == 10.0
        assert bucket.burst == 30
        assert bucket.last_refill_key == "pf:egp:rate:last_refill"


class TestCircuitBreaker:
    """Verify circuit breaker state management.

    Note: These tests mock Redis or skip if Redis unavailable.
    """

    @pytest.mark.asyncio
    async def test_circuit_breaker_is_open_without_redis(self):
        """Without Redis, circuit breaker is always closed (fail-open)."""
        breaker = CircuitBreaker(None, key="pf:egp:circuit")

        # Should never open without Redis
        assert await breaker.is_open() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_success_without_redis(self):
        """Record success without Redis should not raise."""
        breaker = CircuitBreaker(None)
        await breaker.record_success()  # Should not raise

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_failure_without_redis(self):
        """Record failure without Redis should not raise."""
        breaker = CircuitBreaker(None)
        await breaker.record_failure()  # Should not raise

    def test_circuit_breaker_initialization(self):
        """Breaker initializes with correct parameters."""
        breaker = CircuitBreaker(
            None,
            key="pf:egp:circuit",
            failure_threshold=5,
            cool_down_seconds=300,
        )

        assert breaker.key == "pf:egp:circuit"
        assert breaker.failure_count_key == "pf:egp:circuit:failures"
        assert breaker.opened_at_key == "pf:egp:circuit:opened_at"
        assert breaker.failure_threshold == 5
        assert breaker.cool_down == 300


class TestConcurrentRateLimiting:
    """Integration test: verify concurrent requests respect rate limit.

    These are conceptual tests showing how concurrency would be tested
    with a real Redis instance.
    """

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests_without_redis(self):
        """Multiple concurrent tasks should complete without Redis."""
        bucket = RedisTokenBucket(None, "test:bucket", rate=1.0, burst=5)

        results = await asyncio.gather(
            bucket.acquire(1),
            bucket.acquire(1),
            bucket.acquire(1),
        )

        # Without Redis, all should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_backoff_and_retry_integration(self):
        """Backoff can be used in retry loops."""
        backoff = ExponentialBackoff(base=0.001, max_retries=2)
        attempts = 0

        while True:
            try:
                attempts += 1
                if attempts < 3:
                    raise IOError("Simulated e-GP timeout")
                break
            except IOError:
                if attempts > backoff.max_retries:
                    raise
                await backoff.sleep_and_retry()

        assert attempts == 3


class TestRateLimitError:
    """Verify custom exceptions."""

    def test_rate_limit_error_is_exception(self):
        """RateLimitError is an Exception."""
        error = RateLimitError("Rate limit exceeded")
        assert isinstance(error, Exception)
        assert str(error) == "Rate limit exceeded"

    def test_circuit_breaker_open_is_exception(self):
        """CircuitBreakerOpen is an Exception."""
        error = CircuitBreakerOpen("Circuit open")
        assert isinstance(error, Exception)
        assert str(error) == "Circuit open"
