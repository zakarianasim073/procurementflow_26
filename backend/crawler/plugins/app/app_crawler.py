from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from ...framework.config import settings
from ...framework.extractor import extract_label_value_map, get_field, extract_table_rows, extract_links
from ...framework.logger import get_logger
from ...framework.metrics import track_duration
from ...framework.retry import with_retry
from ...framework.storage import save_raw_record
from ...utils.app_listings import crawl_all_fys, ALL_FYS, parse_listing_row
from ...utils.helpers import normalize_package_no
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.app")


@register("app")
class APPCrawler(BaseCrawler):
    name = "app"

    async def execute(self):
        search_mode = self.ctx.config.get("search_mode", "details")
        if search_mode == "listings":
            return await self._execute_listings()
        return await super().execute()

    async def _execute_listings(self):
        self.ctx._crawl_log.start()
        self._running = True
        try:
            await self.setup()
            output_dir = settings.output_dir / "APP_BY_FY"
            start_fy = self.ctx.config.get("start_fy")
            max_pages = self.ctx.config.get("max_pages")
            results = crawl_all_fys(
                output_dir=output_dir,
                start_fy=start_fy,
                max_pages=max_pages,
            )
            total = sum(results.values())
            self.ctx.items_saved = total
            self.ctx._crawl_log.finish("success")
            log.info("listings_crawl_complete", fys=len(results), total=total)
        except Exception as e:
            self.ctx.log.error("listings_crawl_failed", error=str(e))
            self.ctx._crawl_log.finish("failed", str(e))
        finally:
            self._running = False
        return self.ctx._crawl_log

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()
        nav = self.get_navigator(self.page)
        start_url = settings.url("/resources/common/DeptTree.jsp?operation=AdvAPPSearch")
        await nav.goto(start_url)

    async def parse_list(self) -> List[Dict[str, Any]]:
        links = await self.page.query_selector_all("a")
        budget_links = []
        for link in links:
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            if href and "StdSearch" in href and text in ("DB", "RB", "OF"):
                budget_links.append(href)
        self._budget_links = budget_links
        self._current_budget_idx = 0
        return budget_links

    async def open_details(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"budget_href": item}

    async def parse_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        all_items = []
        for blink in self._budget_links:
            list_page = await self.context.new_page()
            url = blink if blink.startswith("http") else settings.url(blink)
            nav = self.get_navigator(list_page)
            await nav.goto(url)

            for _ in range(self.ctx.max_pages):
                pkg_links = await list_page.query_selector_all("a[href*='ViewPackageDetail']")
                hrefs = [await l.get_attribute("href") for l in pkg_links]

                for href in hrefs:
                    if not href:
                        continue
                    try:
                        detail_page = await self.context.new_page()
                        full_url = href if href.startswith("http") else settings.url(href)
                        await self.get_navigator(detail_page).goto(full_url)
                        kv = await extract_label_value_map(detail_page)
                        lot_rows = await extract_table_rows(detail_page, "table")
                        lots = [
                            {"lot_no": r[0], "lot_description": r[1], "qty": r[2], "unit": r[3], "estimated_cost_bdt": r[4]}
                            for r in lot_rows if len(r) >= 5 and r[0].strip().isdigit()
                        ]
                        data = {
                            "app_id": get_field(kv, "APP ID"),
                            "pkg_id": self._pkg_id(href),
                            "app_code": get_field(kv, "APP Code"),
                            "financial_year": get_field(kv, "Financial Year"),
                            "ministry": get_field(kv, "Ministry"),
                            "organization": get_field(kv, "Organization"),
                            "pe_office": get_field(kv, "PE Office and Code"),
                            "budget_type": get_field(kv, "Budget Type"),
                            "project_name": get_field(kv, "Project Name"),
                            "district": get_field(kv, "District"),
                            "package_no": get_field(kv, "Package No"),
                            "package_description": get_field(kv, "Package Description"),
                            "package_estimated_cost_bdt": get_field(kv, "Package Estimated Cost"),
                            "category": get_field(kv, "Category"),
                            "procurement_method": get_field(kv, "Procurement Method"),
                            "procurement_type": get_field(kv, "Procurement Type"),
                            "source_of_fund": get_field(kv, "Source of Fund"),
                            "exp_advertisement_date": get_field(kv, "Expected Date of Advertisement"),
                            "exp_contract_signing_date": get_field(kv, "Expected Date of Signing of Contract"),
                            "exp_completion_date": get_field(kv, "Expected Date of Completion of Contract"),
                            "total_time_to_signing_days": get_field(kv, "Total Time to Contract Signing"),
                            "lots": lots,
                            "raw": kv,
                        }
                        if data.get("app_id"):
                            all_items.append(data)
                        await detail_page.close()
                        await asyncio.sleep(self.ctx.config.get("rate_limit", 2.0))
                    except Exception as e:
                        log.error("app_item_failed", error=str(e), href=href)

                next_btn = await list_page.query_selector("a:has-text('Next')")
                if next_btn:
                    await next_btn.click()
                    await self.get_navigator(list_page).wait_ready()
                else:
                    break
            await list_page.close()
        return {"items": all_items}

    async def save(self, item: Dict[str, Any]) -> bool:
        items = item.get("items", [])
        saved = 0
        for data in items:
            save_raw_record("raw_app_packages", "eprocure_app", data)
            saved += 1
        self.ctx.items_saved += saved
        return saved > 0

    async def next_page(self) -> bool:
        return False

    async def finish(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.browser_manager.release_context(self.context)

    def _pkg_id(self, href: str) -> str:
        m = re.search(r"pkgId=(\d+)", href)
        return m.group(1) if m else ""
