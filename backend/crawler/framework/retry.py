from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, List, Optional, Tuple, Type, Union

from playwright.async_api import TimeoutError as PWTimeout

from .config import settings
from .logger import get_logger
from .metrics import record_retry

log = get_logger("crawler.retry")

DEFAULT_RETRY_EXCEPTIONS = (PWTimeout, ConnectionError, TimeoutError, OSError)


def with_retry(
    fn: Optional[Callable] = None,
    *,
    max_attempts: int = None,
    base_delay: float = None,
    max_delay: float = None,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = None,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    max_attempts = max_attempts or settings.retry_max_attempts
    base_delay = base_delay or settings.retry_base_delay_s
    max_delay = max_delay or settings.retry_max_delay_s
    exceptions = exceptions or DEFAULT_RETRY_EXCEPTIONS

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                        if jitter:
                            import random
                            delay *= random.uniform(0.5, 1.5)
                        record_retry()
                        log.warning(
                            "retry_attempt",
                            func=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay=round(delay, 2),
                            error=e,
                        )
                        await asyncio.sleep(delay)
                    else:
                        log.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=max_attempts,
                            error=e,
                        )
            raise last_exception

        return wrapper

    if fn:
        return decorator(fn)
    return decorator


def exponential_backoff(attempt: int, base: float = 2.0, max_delay: float = 30.0) -> float:
    import random
    delay = min(base * (2 ** attempt), max_delay)
    return delay * random.uniform(0.5, 1.5)


async def retry_async(
    fn: Callable,
    *args,
    max_attempts: int = None,
    base_delay: float = None,
    **kwargs,
) -> Any:
    max_attempts = max_attempts or settings.retry_max_attempts
    base_delay = base_delay or settings.retry_base_delay_s
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                delay = exponential_backoff(attempt, base=base_delay)
                record_retry()
                log.warning("retry_operation", func=fn.__name__, attempt=attempt, delay=round(delay, 2))
                await asyncio.sleep(delay)

    raise last_error
