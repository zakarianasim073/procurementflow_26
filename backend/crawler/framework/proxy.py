from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .config import settings
from .logger import get_logger
from .metrics import record_error

log = get_logger("crawler.proxy")


@dataclass
class ProxyRecord:
    url: str
    healthy: bool = True
    last_checked: float = 0.0
    latency_ms: float = 0.0
    fail_count: int = 0
    success_count: int = 0
    region: str = ""


class ProxyManager:
    def __init__(self):
        self._proxies: List[ProxyRecord] = []
        self._current_index: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()
        self._health_task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def start(self):
        self._running = True
        await self._load_proxies()
        if self._proxies:
            log.info("proxy_manager_started", count=len(self._proxies))
        else:
            log.info("proxy_manager_no_proxies")
        if settings.proxy_enabled and settings.proxy_rotation and len(self._proxies) > 1:
            self._health_task = asyncio.create_task(self._health_loop())
            log.info("proxy_health_loop_started")

    async def _load_proxies(self):
        if settings.proxy_url and not settings.proxy_list:
            self._proxies.append(ProxyRecord(url=settings.proxy_url))
            return
        for url in settings.proxy_list:
            self._proxies.append(ProxyRecord(url=url))

    async def stop(self):
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        log.info("proxy_manager_stopped")

    async def get_proxy(self) -> Optional[str]:
        if not settings.proxy_enabled or not self._proxies:
            return None
        async with self._lock:
            healthy = [p for p in self._proxies if p.healthy]
            if not healthy:
                log.warning("no_healthy_proxies_available")
                record_error("no_healthy_proxies")
                return None
            if settings.proxy_rotation:
                record = healthy[self._current_index % len(healthy)]
                self._current_index += 1
            else:
                record = healthy[0]
            return record.url

    async def _check_proxy(self, proxy: ProxyRecord) -> bool:
        try:
            start = asyncio.get_event_loop().time()
            async with httpx.AsyncClient(
                proxies=proxy.url,
                verify=True,
                timeout=httpx.Timeout(settings.proxy_health_check_timeout_s),
            ) as client:
                resp = await client.get(settings.proxy_health_check_url)
                latency = (asyncio.get_event_loop().time() - start) * 1000
                proxy.latency_ms = round(latency, 2)
                proxy.last_checked = start
                proxy.healthy = resp.status_code == 200
                if proxy.healthy:
                    proxy.success_count += 1
                    proxy.fail_count = 0
                else:
                    proxy.fail_count += 1
                    record_error("proxy_unhealthy")
                return proxy.healthy
        except Exception as e:
            proxy.healthy = False
            proxy.fail_count += 1
            log.debug("proxy_check_failed", proxy=proxy.url, error=str(e))
            return False

    async def check_all(self) -> List[bool]:
        results = await asyncio.gather(
            *[self._check_proxy(p) for p in self._proxies],
            return_exceptions=True,
        )
        healthy_count = sum(1 for r in results if r is True)
        log.info("proxy_health_check", total=len(self._proxies), healthy=healthy_count)
        return list(results)

    async def _health_loop(self):
        while self._running:
            await asyncio.sleep(120)
            await self.check_all()

    @property
    def healthy_count(self) -> int:
        return sum(1 for p in self._proxies if p.healthy)

    @property
    def all_proxies(self) -> List[ProxyRecord]:
        return list(self._proxies)


_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


async def init_proxy_manager():
    mgr = get_proxy_manager()
    await mgr.start()
    return mgr


async def shutdown_proxy_manager():
    mgr = get_proxy_manager()
    await mgr.stop()
