from __future__ import annotations

import asyncio
import traceback
from typing import Any, Dict, List, Optional

from ...framework.config import settings
from ...framework.logger import get_logger
from ...framework.session import get_session_manager
from ...framework.storage import save_raw_record
from ...database.repository import CrawlRepository
from ..base import BaseCrawler
from ..registry import register
from ...utils.egp_parsers import fetch_award_pages_async, parse_award_detail_html, BASE_URL

log = get_logger("crawler.award")


@register("award")
class AwardCrawler(BaseCrawler):
    name = "award"

    async def execute(self):
        search_mode = self.ctx.config.get("search_mode", "listings")
        if search_mode == "listings":
            return await self._execute_listings()
        return await super().execute()

    async def _execute_listings(self):
        """NOA/award listings via SearchNoaServlet (httpx, no Playwright)."""
        self.ctx._crawl_log.start()
        self._running = True
        try:
            await self.setup()
            max_pages = self.ctx.config.get("max_pages", 50)
            page_size = self.ctx.config.get("page_size", 50)
            timeout = self.ctx.config.get("timeout", 70.0)
            keyword = self.ctx.config.get("keyword", "")
            extract_details = self.ctx.config.get("extract_details", True)
            rate_sleep = self.ctx.config.get("rate_limit", 1.0)

            db_available = False
            try:
                self.ctx.job_id = await CrawlRepository.save_job(
                    self.name, self.ctx.run_id, self.ctx.config
                )
                db_available = True
            except Exception:
                pass

            resume_state = await self._load_listing_checkpoint()
            start_pages: Dict[str, int] = resume_state or {}
            start_page = int(self.ctx.config.get("start_page", start_pages.get("NOA", 1)) or 1)

            session = get_session_manager()
            records = await fetch_award_pages_async(
                session=session,
                max_pages=max_pages,
                page_size=page_size,
                timeout=timeout,
                start_page=start_page,
                keyword=keyword,
            )
            self.ctx.items_extracted += len(records)
            self.ctx.pages_crawled += max(1, len(records) // page_size)
            log.info("award_listings_fetched", count=len(records))

            for record in records:
                try:
                    await self._save_record(record, db_available, extract_details, session, timeout, rate_sleep)
                except Exception as e:
                    self.ctx.items_failed += 1
                    log.warning("award_record_failed", tender_id=record.get("tender_id"), error=str(e))

            self.ctx._crawl_log.progress(
                pages_done=self.ctx.pages_crawled,
                items_done=self.ctx.items_saved,
                items_skipped=self.ctx.items_skipped,
                items_failed=self.ctx.items_failed,
            )
            self.ctx._crawl_log.finish("success")
            log.info("award_listings_complete", total=self.ctx.items_saved, pages=self.ctx.pages_crawled)

        except Exception as e:
            tb = traceback.format_exc()
            self.ctx.log.error("award_listings_failed", error=str(e), traceback=tb)
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

    async def _save_record(self, record, db_available, extract_details, session, timeout, rate_sleep):
        detail_url = record.get("detail_url", "")
        if extract_details and detail_url:
            try:
                client = session.get_client()
                url = detail_url if detail_url.startswith("http") else BASE_URL + detail_url
                det = await client.get(url, timeout=timeout)
                detail = parse_award_detail_html(det.text)
                record.update({k: v for k, v in detail.items() if v})
            except Exception as e:
                log.warning("award_detail_failed", url=detail_url, error=str(e))
            await asyncio.sleep(rate_sleep)

        # Align list fields with normalizer expectations
        if not record.get("economic_operator_name"):
            record["economic_operator_name"] = record.get("winner", "")
        if not record.get("contract_value_bdt"):
            record["contract_value_bdt"] = record.get("amount_bdt")
        record.setdefault("pe_name", record.get("pe_office") or record.get("procuring_entity", ""))
        if not record.get("title"):
            record["title"] = record.get("award_for") or record.get("title", "")

        save_raw_record("raw_awards", "eprocure_award", record)

        if db_available and record.get("tender_id"):
            try:
                from ...database.normalizer import get_normalizer
                normalizer = get_normalizer()
                nid, is_new, n_changes = await normalizer.upsert_award(record)
                if is_new:
                    self.ctx.items_normalized = getattr(self.ctx, "items_normalized", 0) + 1
                elif n_changes:
                    self.ctx.items_updated = getattr(self.ctx, "items_updated", 0) + 1
            except Exception as ne:
                log.warning("award_normalize_failed", tender_id=record.get("tender_id"), error=str(ne))

        self.ctx.items_saved += 1

    async def _load_listing_checkpoint(self) -> Optional[dict]:
        try:
            cp = await CrawlRepository.get_checkpoint(self.name, "award_listing_pages")
            return cp if cp else None
        except Exception:
            pass
        try:
            path = settings.checkpoint_path / "award_listing_pages.json"
            if path.exists():
                import json
                return json.loads(path.read_text())
        except Exception:
            pass
        return None

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()
        nav = self.get_navigator(self.page)
        await nav.goto(settings.url("SearchNOA.jsp"))

    async def parse_list(self) -> List[Dict[str, Any]]:
        links = await self.page.query_selector_all("a")
        items = []
        for link in links:
            href = await link.get_attribute("href")
            if href and "ViewAwardedContracts" in href:
                items.append({"href": href})
        return items

    async def open_details(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            detail_page = await self.context.new_page()
            href = item["href"]
            url = href if href.startswith("http") else settings.url(href)
            await self.get_navigator(detail_page).goto(url)
            kv = await extract_label_value_map(detail_page)
            bo_rows = await extract_table_rows(detail_page, "table")
            owners = [
                {"name": r[1], "ownership_pct": r[2], "country": r[3] if len(r) > 3 else None}
                for r in bo_rows if len(r) >= 3 and r[0].strip().isdigit()
            ]
            await detail_page.close()
            return {"href": href, "kv": kv, "beneficial_owners": owners}
        except Exception as e:
            log.error("award_detail_failed", error=str(e), href=item.get("href"))
            return None

    async def parse_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        kv = item.get("kv", {})
        return {
            "tender_id": get_field(kv, "Tender/Proposal ID"),
            "reference_no": get_field(kv, "Invitation/Proposal Reference No"),
            "ministry": get_field(kv, "Ministry/Division"),
            "pe_name": get_field(kv, "Procuring Entity Name"),
            "award_for": get_field(kv, "Contract Award for"),
            "procurement_method": get_field(kv, "Procurement Method"),
            "package_no": get_field(kv, "Tender/Proposal Package No"),
            "contract_value_bdt": get_field(kv, "Contract Value"),
            "economic_operator_name": get_field(kv, "Name of the Economic Operator"),
            "economic_operator_id": get_field(kv, "Tenderer ID of the Economic Operator"),
            "contract_signing_date": get_field(kv, "Date of Contract Signing"),
            "beneficial_owners": item.get("beneficial_owners", []),
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
        if hasattr(self, "page") and self.page:
            try:
                await self.page.close()
            except Exception:
                pass
        if hasattr(self, "context") and self.context:
            try:
                await self.browser_manager.release_context(self.context)
            except Exception:
                pass


# Local imports kept at bottom to avoid circular import at module load
from ...framework.extractor import extract_label_value_map, get_field, extract_table_rows  # noqa: E402
