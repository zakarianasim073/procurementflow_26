from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from ...framework.config import settings
from ...framework.extractor import extract_table_rows, extract_label_value_map
from ...framework.logger import get_logger
from ...framework.storage import save_raw_record
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.offline_tender")

APP_ID_PATTERN = re.compile(r"APP ID\s*:\s*(\d+)")


@register("offline_tender")
class OfflineTenderCrawler(BaseCrawler):
    name = "offline_tender"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()
        nav = self.get_navigator(self.page)
        start_url = settings.url("SearchTenderOffline.jsp")
        await nav.goto(start_url)

    async def parse_list(self) -> List[Dict[str, Any]]:
        rows = await extract_table_rows(self.page, "table")
        view_links = await self.page.query_selector_all("a:has-text('View')")
        hrefs = [await l.get_attribute("href") for l in view_links]
        items = []
        idx = 0
        for row in rows:
            if len(row) < 6 or not row[0].strip().isdigit():
                continue
            ref_field = row[1]
            app_match = APP_ID_PATTERN.search(ref_field)
            lines = ref_field.split("\n")
            tender_id = lines[0].strip() if lines else None
            reference_no = lines[1].strip() if len(lines) > 1 else None
            title_lines = row[2].split("\n")
            org_lines = row[3].split("\n")
            method_lines = row[4].split("\n")
            date_lines = row[5].split("\n")
            href = hrefs[idx] if idx < len(hrefs) else None
            item = {
                "s_no": row[0],
                "tender_id": tender_id,
                "reference_no": reference_no,
                "app_id_embedded": app_match.group(1) if app_match else None,
                "procurement_nature": title_lines[0] if title_lines else None,
                "title": title_lines[1] if len(title_lines) > 1 else None,
                "ministry": org_lines[0] if len(org_lines) > 0 else None,
                "organization": org_lines[1] if len(org_lines) > 1 else None,
                "pe_name": org_lines[2] if len(org_lines) > 2 else None,
                "procurement_type": method_lines[0] if method_lines else None,
                "procurement_method": method_lines[1] if len(method_lines) > 1 else None,
                "publishing_date": date_lines[0] if date_lines else None,
                "closing_date": date_lines[1] if len(date_lines) > 1 else None,
                "detail_href": href,
            }
            if href:
                try:
                    detail_page = await self.context.new_page()
                    url = href if href.startswith("http") else settings.url(href)
                    await self.get_navigator(detail_page).goto(url)
                    kv = await extract_label_value_map(detail_page)
                    item["detail_raw"] = kv
                    await detail_page.close()
                    await asyncio.sleep(self.ctx.config.get("rate_limit", 2.0))
                except Exception as e:
                    log.error("offline_tender_detail_failed", error=str(e), href=href)
            items.append(item)
            idx += 1
        return items

    async def next_page(self) -> bool:
        next_btn = await self.page.query_selector("a:has-text('Next')")
        if next_btn:
            await next_btn.click()
            await self.page.wait_for_load_state("networkidle")
            return True
        return False

    async def finish(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.browser_manager.release_context(self.context)
