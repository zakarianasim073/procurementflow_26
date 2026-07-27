from __future__ import annotations

import asyncio
import traceback
from typing import Any, Dict, List, Optional

from ...framework.config import settings
from ...framework.extractor import extract_label_value_map, get_field
from ...framework.logger import get_logger
from ...framework.session import get_session_manager
from ...framework.storage import save_raw_record, get_storage_manager
from ...utils.egp_parsers import (
    fetch_tender_pages,
    fetch_tender_pages_async,
)
from ...database.repository import CrawlRepository
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.tender")


@register("tender")
class TenderCrawler(BaseCrawler):
    name = "tender"

    async def execute(self):
        search_mode = self.ctx.config.get("search_mode", "listings")
        if search_mode == "listings":
            return await self._execute_listings()
        return await super().execute()

    async def _execute_listings(self):
        """Phase 2: Listings with pagination + detail extraction + change detection."""
        self.ctx._crawl_log.start()
        self._running = True
        try:
            await self.setup()
            view_types = self.ctx.config.get("view_types", ["Live"])
            max_pages = self.ctx.config.get("max_pages", 100)
            page_size = self.ctx.config.get("page_size", 50)
            timeout = self.ctx.config.get("timeout", 70.0)
            extract_details = self.ctx.config.get("extract_details", False)
            detect_changes = self.ctx.config.get("detect_changes", True)

            db_available = False
            try:
                self.ctx.job_id = await CrawlRepository.save_job(
                    self.name, self.ctx.run_id, self.ctx.config
                )
                db_available = True
            except Exception:
                pass

            resume_enabled = self.ctx.config.get("resume", True) and not self.ctx.config.get("reset_checkpoint", False)
            if self.ctx.config.get("reset_checkpoint", False):
                await self._clear_listing_checkpoint()
                log.info("checkpoint_reset", view_types=view_types)

            resume_state = await self._load_listing_checkpoint() if resume_enabled else None
            start_pages: Dict[str, int] = resume_state or {}

            for view_type in view_types:
                start_page = int(self.ctx.config.get("start_page", start_pages.get(view_type, 1)) or 1)
                log.info("fetching_view", view=view_type, start_page=start_page, max_pages=max_pages)

                async def checkpoint_fn(page: int, total: int):
                    if settings.checkpoint_enabled:
                        await self._save_listing_checkpoint({
                            view_type: page + 1,
                        })

                session = get_session_manager()
                records = await fetch_tender_pages_async(
                    session=session,
                    view_type=view_type,
                    max_pages=max_pages,
                    page_size=page_size,
                    timeout=timeout,
                    start_page=start_page,
                    checkpoint_callback=checkpoint_fn,
                )
                if not records and start_page > 1:
                    log.warning("resume_empty_fallback",
                                view=view_type, start_page=start_page,
                                msg="resumed page empty, retrying from page 1")
                    start_page = 1
                    await self._save_listing_checkpoint({view_type: 1})
                    records = await fetch_tender_pages_async(
                        session=session,
                        view_type=view_type,
                        max_pages=max_pages,
                        page_size=page_size,
                        timeout=timeout,
                        start_page=start_page,
                        checkpoint_callback=checkpoint_fn,
                    )
                self.ctx.items_extracted += len(records)
                self.ctx.pages_crawled += max(1, len(records) // page_size)
                log.info("tender_view_fetched", view=view_type, count=len(records))

                for record in records:
                    try:
                        await self._save_record(record, db_available, detect_changes)
                    except Exception as e:
                        self.ctx.items_failed += 1
                        log.warning("record_save_failed", tender_id=record.get("tender_id"), error=str(e))

            self.ctx._crawl_log.progress(
                pages_done=self.ctx.pages_crawled,
                items_done=self.ctx.items_saved,
                items_skipped=self.ctx.items_skipped,
                items_failed=self.ctx.items_failed,
            )
            self.ctx._crawl_log.finish("success")
            log.info("tender_listings_complete",
                     total=self.ctx.items_saved,
                     pages=self.ctx.pages_crawled)

        except Exception as e:
            tb = traceback.format_exc()
            self.ctx.log.error("tender_listings_failed", error=str(e), traceback=tb)
            self.ctx._crawl_log.finish("failed", str(e) + "\n" + tb)
        finally:
            if self.ctx.job_id:
                try:
                    await CrawlRepository.finish_job(
                        self.ctx.job_id, self.ctx._crawl_log.status,
                        pages=self.ctx.pages_crawled,
                        items=self.ctx.items_saved,
                        skipped=self.ctx.items_skipped,
                        failed=self.ctx.items_failed,
                    )
                except Exception:
                    pass
            self._running = False
        return self.ctx._crawl_log

    async def _save_record(self, record: dict, db_available: bool, detect_changes: bool):
        tender_id = record.get("tender_id", "")
        save_raw_record("raw_tenders", "eprocure_tender", record)

        if db_available and tender_id:
            if detect_changes:
                changes = await CrawlRepository.detect_changes(tender_id, record)
                if changes:
                    last = await CrawlRepository.get_last_tender_record(tender_id)
                    await CrawlRepository.log_change(
                        table="raw_tenders",
                        record_id=tender_id,
                        change_type="updated",
                        previous=last["data"] if last else None,
                        new_data=record,
                        fields=changes,
                    )
                    log.info("tender_change_detected", tender_id=tender_id, fields=list(changes.keys()))
            await CrawlRepository.save_tender_record(tender_id, record)

            # Phase 3: Normalize raw record into canonical pf_* tables
            try:
                from ...database.normalizer import get_normalizer
                normalizer = get_normalizer()
                nid, is_new, n_changes = await normalizer.upsert_tender(record)
                if is_new:
                    self.ctx.items_normalized = getattr(self.ctx, "items_normalized", 0) + 1
                elif n_changes:
                    self.ctx.items_updated = getattr(self.ctx, "items_updated", 0) + 1
                    log.info("tender_normalized_change", tender_id=tender_id,
                             fields=list(n_changes.keys()))
            except Exception as ne:
                log.warning("tender_normalize_failed", tender_id=tender_id, error=str(ne))

        self.ctx.items_saved += 1

    async def _clear_listing_checkpoint(self):
        try:
            await CrawlRepository.clear_checkpoint(self.name, "tender_listing_pages")
        except Exception:
            pass
        try:
            path = settings.checkpoint_path / "tender_listing_pages.json"
            if path.exists():
                path.unlink()
        except Exception:
            pass

    async def _load_listing_checkpoint(self) -> Optional[dict]:
        try:
            cp = await CrawlRepository.get_checkpoint(self.name, "tender_listing_pages")
            return cp if cp else None
        except Exception:
            pass
        try:
            path = settings.checkpoint_path / "tender_listing_pages.json"
            if path.exists():
                import json
                return json.loads(path.read_text())
        except Exception:
            pass
        return None

    async def _save_listing_checkpoint(self, data: dict):
        try:
            await CrawlRepository.save_checkpoint(self.name, "tender_listing_pages", data)
        except Exception:
            settings.checkpoint_path.mkdir(parents=True, exist_ok=True)
            import json
            path = settings.checkpoint_path / "tender_listing_pages.json"
            existing = {}
            if path.exists():
                existing = json.loads(path.read_text())
            existing.update(data)
            path.write_text(json.dumps(existing))

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()
        nav = self.get_navigator(self.page)
        start_url = settings.url("AllTenders.jsp?h=t")
        await nav.goto(start_url)

    async def parse_list(self) -> List[Dict[str, Any]]:
        rows = await self.page.query_selector_all("table tr")
        items = []
        for row in rows:
            link = await row.query_selector("a")
            if link:
                href = await link.get_attribute("href")
                if href and "ViewTender" in href:
                    items.append({"href": href, "_row": row})
        return items

    async def open_details(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            detail_page = await self.context.new_page()
            href = item["href"]
            url = href if href.startswith("http") else settings.url(href)
            await self.get_navigator(detail_page).goto(url)
            kv = await extract_label_value_map(detail_page)
            await detail_page.close()
            return {"href": href, "kv": kv}
        except Exception as e:
            log.error("tender_detail_failed", error=str(e), href=item.get("href"))
            return None

    async def parse_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        kv = item.get("kv", {})
        return {
            "tender_id": get_field(kv, "Tender/Proposal ID"),
            "app_id": get_field(kv, "App ID"),
            "reference_no": get_field(kv, "Invitation Reference No"),
            "status": get_field(kv, "Tender/Proposal Status"),
            "ministry": get_field(kv, "Ministry"),
            "organization": get_field(kv, "Organization"),
            "procuring_entity_name": get_field(kv, "Procuring Entity Name"),
            "procurement_nature": get_field(kv, "Procurement Nature"),
            "procurement_type": get_field(kv, "Procurement Type"),
            "procurement_method": get_field(kv, "Procurement Method"),
            "package_no": get_field(kv, "Tender/Proposal Package No"),
            "publish_datetime": get_field(kv, "Date and Time"),
            "closing_datetime": get_field(kv, "Tender/Proposal Closing"),
            "document_price_bdt": get_field(kv, "Tender/Proposal Document Price"),
            "category": get_field(kv, "Category"),
            "earnest_money_bdt": get_field(kv, "Earnest Money"),
            "raw": kv,
        }

    async def next_page(self) -> bool:
        next_btn = await self.page.query_selector("a:has-text('Next')")
        if next_btn:
            await next_btn.click()
            await self.get_navigator(self.page).wait_ready()
            return True
        return False

    async def finish(self):
        if hasattr(self, 'page') and self.page:
            try:
                await self.page.close()
            except Exception:
                pass
        if hasattr(self, 'context') and self.context:
            try:
                await self.browser_manager.release_context(self.context)
            except Exception:
                pass
