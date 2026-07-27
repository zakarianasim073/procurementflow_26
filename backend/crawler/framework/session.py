from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx

from .config import settings
from .logger import get_logger
from .proxy import get_proxy_manager
from .rate_limiter import get_rate_limiter
from .url_policy import validate_crawler_url

log = get_logger("crawler.session")


@dataclass
class SessionRecord:
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    last_used: float = 0.0
    created_at: float = 0.0


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def start(self):
        proxy_url = None
        if settings.proxy_enabled:
            try:
                proxy_mgr = get_proxy_manager()
                proxy_url = await proxy_mgr.get_proxy()
            except Exception:
                proxy_url = settings.proxy_url

        client_kwargs = dict(
            verify=True,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=15.0, read=30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
        if proxy_url:
            client_kwargs["proxies"] = proxy_url
            log.info("session_proxy_enabled", proxy=proxy_url)

        self._http_client = httpx.AsyncClient(**client_kwargs)
        log.info("session_manager_started")

    async def stop(self):
        if self._http_client:
            await self._http_client.aclose()
        log.info("session_manager_stopped")

    def get_client(self) -> httpx.AsyncClient:
        if not self._http_client:
            raise RuntimeError("SessionManager not started")
        return self._http_client

    def get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    async def http_get(self, url: str, **kwargs) -> httpx.Response:
        validate_crawler_url(url)
        client = self.get_client()
        domain = self.get_domain(url)
        rate_limiter = get_rate_limiter()
        for attempt in range(settings.retry_max_attempts):
            try:
                await rate_limiter.acquire(domain)
                resp = await client.get(url, **kwargs)
                resp.raise_for_status()
                rate_limiter.record_success()
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = settings.retry_base_delay_s * (2 ** attempt)
                    log.warning("rate_limited", url=url, wait=wait, attempt=attempt)
                    await asyncio.sleep(wait)
                    continue
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                rate_limiter.record_error()
                if attempt < settings.retry_max_attempts - 1:
                    wait = settings.retry_base_delay_s * (2 ** attempt)
                    log.warning("http_retry", url=url, wait=wait, attempt=attempt, error=e)
                    await asyncio.sleep(wait)
                    continue
                raise

    async def http_post(self, url: str, data: Optional[dict] = None, **kwargs) -> httpx.Response:
        validate_crawler_url(url)
        client = self.get_client()
        domain = self.get_domain(url)
        await get_rate_limiter().acquire(domain)
        response = await client.post(url, data=data, **kwargs)
        response.raise_for_status()
        return response


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def init_session_manager():
    mgr = get_session_manager()
    await mgr.start()
    return mgr


async def shutdown_session_manager():
    mgr = get_session_manager()
    await mgr.stop()
