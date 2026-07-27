from __future__ import annotations

import asyncio
import json
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..framework.browser import BrowserManager
from ..framework.captcha import CAPTCHASolver
from ..framework.config import settings, CrawlMode
from ..framework.deduplicator import get_deduplicator
from ..framework.downloader import DocumentDownloader
from ..framework.logger import get_logger, CrawlerLogRecord
from ..framework.metrics import get_metrics, CrawlerMetrics
from ..framework.navigator import Navigator
from ..framework.proxy import ProxyManager
from ..framework.rate_limiter import AdaptiveRateLimiter, get_rate_limiter
from ..framework.retry import with_retry
from ..framework.session import SessionManager
from ..framework.storage import get_storage_manager
from ..framework.validator import DataValidator, ValidationResult

from ..database.repository import CrawlRepository


class CrawlContext:
    def __init__(self, plugin: str, config: Optional[dict] = None):
        self.plugin = plugin
        self.run_id = str(uuid4())[:12]
        self.config = config or {}
        self.mode = CrawlMode(self.config.get("mode", "incremental"))
        self.max_pages = self.config.get("max_pages", 10)
        self.checkpoint_key = self.config.get("checkpoint_key", plugin)
        self.items: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.pages_crawled: int = 0
        self.items_extracted: int = 0
        self.items_saved: int = 0
        self.items_skipped: int = 0
        self.items_failed: int = 0
        self.metrics = CrawlerMetrics()
        self.job_id: Optional[int] = None
        self.resume_state: Optional[dict] = None
        self.start_time: Optional[str] = None
        self.log = get_logger(f"crawl.{plugin}")
        self._crawl_log = CrawlerLogRecord(plugin, self.run_id)


class BaseCrawler(ABC):
    name: str = "base"
    version: str = "1.0.0"

    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        session_manager: Optional[SessionManager] = None,
        config: Optional[dict] = None,
        proxy_manager: Optional[ProxyManager] = None,
        captcha_solver: Optional[CAPTCHASolver] = None,
    ):
        self.browser_manager = browser_manager
        self.session_manager = session_manager
        self.proxy_manager = proxy_manager
        self.captcha_solver = captcha_solver
        self.rate_limiter = get_rate_limiter()
        self.config = config or {}
        self.ctx = CrawlContext(self.name, self.config)
        self._page_pool: List = []
        self._navigators: Dict = {}
        self.downloader: Optional[DocumentDownloader] = None
        self.storage = get_storage_manager()
        self.dedup = get_deduplicator()
        self.validator = DataValidator()
        self._running = False

    async def setup(self):
        if settings.checkpoint_enabled:
            self.ctx.resume_state = await self._load_checkpoint()
        if self.ctx.mode == CrawlMode.RESUME and self.ctx.resume_state:
            self.ctx.log.info("resuming_from_checkpoint", state=self.ctx.resume_state)
        self.storage = get_storage_manager()
        self.dedup = get_deduplicator()
        self.ctx.start_time = datetime.now(timezone.utc).isoformat()

    async def execute(self) -> CrawlerLogRecord:
        self.ctx._crawl_log.start()
        self._running = True
        _failed = False
        try:
            await self.setup()
            db_available = False
            if settings.storage_backend in ("postgresql", "both"):
                try:
                    self.ctx.job_id = await CrawlRepository.save_job(
                        self.name, self.ctx.run_id, self.config
                    )
                    db_available = True
                except Exception:
                    pass

            await self.initialize()

            if settings.checkpoint_enabled and self.ctx.resume_state:
                await self._resume_from_checkpoint()
            else:
                await self.search()
                current_page = 0
                while current_page < self.ctx.max_pages and self._running:
                    items_on_page = await self.parse_list()
                    if not items_on_page:
                        break
                    await self._process_items(items_on_page)
                    self.ctx.pages_crawled += 1
                    self.ctx._crawl_log.progress(
                        pages_done=self.ctx.pages_crawled,
                        items_done=self.ctx.items_saved,
                        items_skipped=self.ctx.items_skipped,
                        items_failed=self.ctx.items_failed,
                    )
                    if settings.checkpoint_enabled:
                        await self._save_checkpoint()
                    has_next = await self.next_page()
                    if not has_next:
                        break
                    current_page += 1
                    await asyncio.sleep(settings.rate_limit_min_s)

            await self.finish()
            self.ctx._crawl_log.finish("success")

        except Exception as e:
            _failed = True
            self.ctx.log.error("crawl_execution_failed", error=e, traceback=traceback.format_exc())
            self.ctx._crawl_log.finish("failed", str(e))
            if self.ctx.job_id:
                try:
                    await CrawlRepository.finish_job(
                        self.ctx.job_id, "failed",
                        pages=self.ctx.pages_crawled,
                        items=self.ctx.items_saved,
                        skipped=self.ctx.items_skipped,
                        failed=self.ctx.items_failed,
                        error=str(e),
                    )
                except Exception:
                    pass
        finally:
            self._running = False
            # Only write "completed" when no exception was raised — the except block
            # already wrote "failed" and this finally must not overwrite it.
            if not _failed and self.ctx.job_id:
                try:
                    await CrawlRepository.finish_job(
                        self.ctx.job_id, "completed",
                        pages=self.ctx.pages_crawled,
                        items=self.ctx.items_saved,
                        skipped=self.ctx.items_skipped,
                        failed=self.ctx.items_failed,
                    )
                except Exception:
                    pass

        return self.ctx._crawl_log

    async def initialize(self):
        pass

    @abstractmethod
    async def search(self):
        pass

    @abstractmethod
    async def parse_list(self) -> List[Dict[str, Any]]:
        pass

    async def open_details(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return item

    async def parse_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return item

    async def download_documents(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return item

    async def validate(self, item: Dict[str, Any]) -> ValidationResult:
        return self.validator.validate(item)

    async def save(self, item: Dict[str, Any]) -> bool:
        table = self.config.get("table", f"raw_{self.name}")
        source = self.config.get("source", f"eprocure_{self.name}")
        if self.dedup.is_duplicate(table, item):
            self.ctx.items_skipped += 1
            get_metrics().items_deduplicated.skipped += 1
            return False
        await self.storage.save(table, source, item)
        self.dedup.mark_seen(table, item)
        self.ctx.items_saved += 1
        get_metrics().items_saved.success += 1
        # Phase 3: normalize raw record into canonical pf_* tables
        await self._normalize(item)
        return True

    async def _normalize(self, item: Dict[str, Any]):
        """Dispatch raw record to the Normalizer based on plugin name."""
        from ..database.normalizer import get_normalizer
        try:
            norm = get_normalizer()
            name = self.name
            if name == "tender":
                await norm.upsert_tender(item)
            elif name == "award":
                await norm.upsert_award(item)
            elif name == "offline_award":
                await norm.upsert_award(item, source="offline")
            elif name == "offline_tender":
                await norm.upsert_tender(item, source="offline")
            elif name == "experience":
                await norm.upsert_experience(item)
            elif name == "debarment":
                await norm.upsert_debarment(item)
        except Exception as e:
            # ERROR not WARNING — silent normalization failures mean pf_* tables
            # are silently falling behind raw_crawl_data (data pipeline dark spot).
            self.ctx.log.error("normalize_failed", plugin=self.name, error=str(e))

    async def next_page(self) -> bool:
        return False

    async def finish(self):
        self.dedup.flush()

    async def discover_relationships(self):
        """Run the relationship discovery pass for this plugin's entity type."""
        from ..services.relationship_engine import RelationshipEngine
        try:
            engine = RelationshipEngine()
            cnt = await engine.discover_all()
            self.ctx.log.info("relationships_discovered", plugin=self.name, count=cnt.get("_total", 0))
        except Exception as e:
            self.ctx.log.warning("relationship_discovery_failed", plugin=self.name, error=str(e))

    async def _process_items(self, items: List[Dict[str, Any]]):
        for item in items:
            try:
                detail = await self.open_details(item)
                if detail:
                    parsed = await self.parse_details(detail)
                    with_docs = await self.download_documents(parsed)
                    validation = await self.validate(with_docs)
                    if validation.valid:
                        await self.save(with_docs)
                        self.ctx.items_extracted += 1
                    else:
                        self.ctx.items_failed += 1
                        self.ctx.log.warning("validation_failed", errors=validation.errors)
                await asyncio.sleep(settings.rate_limit_min_s)
            except Exception as e:
                self.ctx.items_failed += 1
                self.ctx.log.error("item_processing_failed", error=e)

    async def _load_checkpoint(self) -> Optional[dict]:
        try:
            return await CrawlRepository.get_checkpoint(self.name, self.ctx.checkpoint_key)
        except Exception:
            checkpoint_path = settings.checkpoint_path / f"{self.name}.json"
            if checkpoint_path.exists():
                return json.loads(checkpoint_path.read_text())
        return None

    async def _save_checkpoint(self):
        data = {
            "pages_crawled": self.ctx.pages_crawled,
            "items_saved": self.ctx.items_saved,
            "last_run": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await CrawlRepository.save_checkpoint(self.name, self.ctx.checkpoint_key, data)
        except Exception:
            settings.checkpoint_path.mkdir(parents=True, exist_ok=True)
            path = settings.checkpoint_path / f"{self.name}.json"
            path.write_text(json.dumps(data))

    async def _resume_from_checkpoint(self):
        self.ctx.pages_crawled = self.ctx.resume_state.get("pages_crawled", 0)
        self.ctx.items_saved = self.ctx.resume_state.get("items_saved", 0)

    @property
    def log(self):
        return self.ctx.log

    @property
    def metrics(self):
        return self.ctx.metrics

    def get_navigator(self, page) -> Navigator:
        return Navigator(page)
