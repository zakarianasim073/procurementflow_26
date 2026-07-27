"""CrawlImportService — Facade orchestrator for production crawler framework.

T-024: Wraps backend/crawler/plugins/* framework (8 domain crawlers).
Uses: APP, Tender, Award, Experience, Debarment, Document crawlers + offline variants.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

# Import from production crawler framework. The framework packages itself as
# `backend.crawler.*` (repo root on sys.path); when running from backend/ the
# repo root may be absent, so add it before importing.
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.crawler.plugins.loader import load_plugin
from backend.crawler.plugins.registry import get_registered_crawlers
from backend.crawler.framework.config import settings, CrawlMode

logger = logging.getLogger(__name__)


class CrawlImportService:
    """Orchestrator facade for production crawler framework.

    Coordinates 8 domain-specific crawlers:
    - APP (Annual Procurement Plans)
    - Tender (live tenders with details)
    - Award (Notice of Awards)
    - Experience (contractor work history)
    - Debarment (banned entities)
    - Document (specifications, BOQ, etc.)
    - OfflineTender, OfflineAward (historical data)
    """

    def __init__(self, db: Session):
        self.db = db
        self.crawlers = get_registered_crawlers()
        self.stats = {
            'app_records': 0,
            'tenders_crawled': 0,
            'awards_collected': 0,
            'documents_extracted': 0,
            'experience_records': 0,
            'debarred_entities': 0,
            'start_time': datetime.now(timezone.utc),
            'end_time': None,
        }

    async def crawl_and_import_all(self, max_pages: int = 50, concurrent_crawlers: int = 3) -> Dict[str, Any]:
        """Orchestrate all 8 crawlers in sequence."""
        self.stats['start_time'] = datetime.now(timezone.utc)
        logger.info(f"[CrawlImport] Starting framework crawls (max {max_pages} pages, {concurrent_crawlers} parallel)")

        try:
            # Run crawlers in priority order
            await self.crawl_app_listings(max_pages=max_pages)
            await self.crawl_live_tenders(max_pages=max_pages)
            await self.crawl_awards(max_pages=max_pages)
            await self.crawl_documents(max_pages=max_pages)
            await self.crawl_experience(max_pages=max_pages)
            await self.crawl_debarment(max_pages=max_pages)

            self.stats['end_time'] = datetime.now(timezone.utc)
            logger.info(f"[CrawlImport] All crawls complete: {self.stats}")
            return self.stats
        except Exception as e:
            logger.error(f"[CrawlImport] Crawl failed: {e}", exc_info=True)
            raise

    async def crawl_app_listings(self, max_pages: int = 50) -> Dict[str, Any]:
        """Run APP (Annual Procurement Plan) crawler."""
        logger.info("[CrawlImport] Running APP crawler")
        try:
            crawler = load_plugin("app")
            config = {"search_mode": "listings", "max_pages": max_pages}
            result = await crawler.execute(config=config)
            self.stats['app_records'] = result.get('items_saved', 0)
            return result
        except Exception as e:
            logger.error(f"[CrawlImport] APP crawl failed: {e}")
            return {"app_records": 0}

    async def crawl_live_tenders(self, max_pages: int = 50) -> Dict[str, Any]:
        """Run Tender crawler for live e-GP tenders."""
        logger.info("[CrawlImport] Running Tender crawler")
        try:
            crawler = load_plugin("tender")
            config = {"mode": "incremental", "max_pages": max_pages}
            result = await crawler.execute(config=config)
            self.stats['tenders_crawled'] = result.get('items_saved', 0)
            return result
        except Exception as e:
            logger.error(f"[CrawlImport] Tender crawl failed: {e}")
            return {"tenders_crawled": 0}

    async def crawl_awards(self, max_pages: int = 50) -> Dict[str, Any]:
        """Run Award crawler for Notice of Awards."""
        logger.info("[CrawlImport] Running Award crawler")
        try:
            crawler = load_plugin("award")
            config = {"search_mode": "listings", "max_pages": max_pages, "extract_details": True}
            result = await crawler.execute(config=config)
            self.stats['awards_collected'] = result.get('items_saved', 0)
            return result
        except Exception as e:
            logger.error(f"[CrawlImport] Award crawl failed: {e}")
            return {"awards_collected": 0}

    async def crawl_documents(self, max_pages: int = 50) -> Dict[str, Any]:
        """Run Document crawler for tender specifications, BOQ, etc."""
        logger.info("[CrawlImport] Running Document crawler")
        try:
            crawler = load_plugin("documents")
            config = {"mode": "incremental", "max_pages": max_pages}
            result = await crawler.execute(config=config)
            self.stats['documents_extracted'] = result.get('items_saved', 0)
            return result
        except Exception as e:
            logger.error(f"[CrawlImport] Document crawl failed: {e}")
            return {"documents_extracted": 0}

    async def crawl_experience(self, max_pages: int = 50) -> Dict[str, Any]:
        """Run Experience crawler for contractor work history."""
        logger.info("[CrawlImport] Running Experience crawler")
        try:
            crawler = load_plugin("experience")
            config = {"max_pages": max_pages}
            result = await crawler.execute(config=config)
            self.stats['experience_records'] = result.get('items_saved', 0)
            return result
        except Exception as e:
            logger.error(f"[CrawlImport] Experience crawl failed: {e}")
            return {"experience_records": 0}

    async def crawl_debarment(self, max_pages: int = 50) -> Dict[str, Any]:
        """Run Debarment crawler for banned entities."""
        logger.info("[CrawlImport] Running Debarment crawler")
        try:
            crawler = load_plugin("debarment")
            config = {"mode": "full", "max_pages": max_pages}
            result = await crawler.execute(config=config)
            self.stats['debarred_entities'] = result.get('items_saved', 0)
            return result
        except Exception as e:
            logger.error(f"[CrawlImport] Debarment crawl failed: {e}")
            return {"debarred_entities": 0}

    def get_stats(self) -> Dict[str, Any]:
        """Return crawl statistics."""
        return self.stats

    def get_available_crawlers(self) -> Dict[str, Any]:
        """List all registered crawlers and their versions."""
        return {name: {"version": info.get("version", "1.0.0")} for name, info in self.crawlers.items()}
