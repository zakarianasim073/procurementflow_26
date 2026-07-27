from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Type

from ..framework.browser import BrowserManager
from ..framework.captcha import CAPTCHASolver, get_captcha_solver, init_captcha_solver, shutdown_captcha_solver
from ..framework.config import settings
from ..framework.downloader import DocumentDownloader
from ..framework.logger import get_logger
from ..framework.proxy import ProxyManager, get_proxy_manager, init_proxy_manager, shutdown_proxy_manager
from ..framework.rate_limiter import AdaptiveRateLimiter, get_rate_limiter
from ..framework.session import SessionManager, init_session_manager, shutdown_session_manager
from ..framework.storage import get_storage_manager
from ..plugins.base import BaseCrawler, CrawlerLogRecord
from ..plugins.registry import list_plugins, get as get_plugin_cls
from .task_queue import TaskQueue, TaskPriority

log = get_logger("crawler.orchestrator")


class CrawlerOrchestrator:
    def __init__(self):
        self.browser: Optional[BrowserManager] = None
        self.session: Optional[SessionManager] = None
        self.downloader: Optional[DocumentDownloader] = None
        self.task_queue: Optional[TaskQueue] = None
        self.proxy: Optional[ProxyManager] = None
        self.captcha: Optional[CAPTCHASolver] = None
        self.rate_limiter: Optional[AdaptiveRateLimiter] = None
        self._running = False

    async def start(self):
        log.info("orchestrator_starting")

        self.proxy = await init_proxy_manager()
        log.info("proxy_manager_started")

        self.browser = BrowserManager()
        await self.browser.start()
        log.info("browser_manager_started")

        self.session = await init_session_manager()
        log.info("session_manager_started")

        self.downloader = DocumentDownloader()
        await self.downloader.start()
        log.info("downloader_started")

        self.captcha = await init_captcha_solver()
        log.info("captcha_solver_started")

        self.rate_limiter = get_rate_limiter()
        log.info("rate_limiter_ready")

        await get_storage_manager().initialize()
        log.info("storage_initialized")

        self.task_queue = TaskQueue(max_concurrent=settings.max_workers)
        await self.task_queue.start()
        log.info("task_queue_started")

        self._running = True
        log.info("orchestrator_started")

    async def stop(self):
        self._running = False
        # Phase 4: Run relationship discovery on existing data
        await self.run_discovery()
        if self.task_queue:
            await self.task_queue.stop()
        if self.downloader:
            await self.downloader.stop()
        await shutdown_captcha_solver()
        if self.session:
            await shutdown_session_manager()
        if self.browser:
            await self.browser.stop()
        await shutdown_proxy_manager()
        log.info("orchestrator_stopped")

    async def run_discovery(self):
        """Run the relationship discovery engine across all pf_* data."""
        from ..services.relationship_engine import RelationshipEngine
        try:
            engine = RelationshipEngine()
            counts = await engine.discover_all()
            total = counts.get("_total", 0)
            if total:
                log.info("orchestrator_discovery_complete", total=total)
        except Exception as e:
            log.warning("orchestrator_discovery_failed", error=str(e))

    async def run_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> CrawlerLogRecord:
        plugin_cls = get_plugin_cls(plugin_name)
        if not plugin_cls:
            raise ValueError(f"Plugin '{plugin_name}' not found. Available: {list_plugins()}")

        crawler: BaseCrawler = plugin_cls(
            browser_manager=self.browser,
            session_manager=self.session,
            config=config or {},
            proxy_manager=self.proxy,
            captcha_solver=self.captcha,
        )
        crawler.downloader = self.downloader

        return await crawler.execute()

    async def run_plugin_async(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.DEFAULT,
    ) -> str:
        task_id = await self.task_queue.enqueue(
            name=plugin_name,
            coro=self.run_plugin,
            priority=priority,
            plugin_name=plugin_name,
            config=config,
        )
        return task_id

    async def run_all(
        self,
        plugin_names: Optional[List[str]] = None,
        configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, CrawlerLogRecord]:
        """Run all plugins concurrently (bounded by the TaskQueue semaphore)."""
        plugins = plugin_names or list_plugins()

        async def _run_one(name: str) -> tuple[str, CrawlerLogRecord]:
            cfg = (configs or {}).get(name, {})
            try:
                return name, await self.run_plugin(name, cfg)
            except Exception as e:
                log.error("plugin_run_failed", plugin=name, error=e)
                rec = CrawlerLogRecord(name)
                rec.finish("failed", str(e))
                return name, rec

        pairs = await asyncio.gather(*[_run_one(n) for n in plugins])
        return dict(pairs)

    def get_task_status(self, task_id: str) -> Any:
        if self.task_queue:
            task = self.task_queue.get_result(task_id)
            if task:
                return {
                    "id": task.id,
                    "name": task.name,
                    "status": task.status.value,
                    "error": task.error,
                }
        return None

    @property
    def is_running(self) -> bool:
        return self._running
