from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ...framework.config import settings
from ...framework.extractor import extract_table_rows, extract_label_value_map
from ...framework.logger import get_logger
from ...framework.storage import save_raw_record
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.offline_award")


def normalize_value_bdt(raw_value: str) -> float:
    try:
        val = float(raw_value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
    if val < 1000:
        return val * 10_000_000
    return val


@register("offline_award")
class OfflineAwardCrawler(BaseCrawler):
    name = "offline_award"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()
        nav = self.get_navigator(self.page)
        start_url = settings.e_gp_base_url + "SearchAwardedContractOffline.jsp"
        await nav.goto(start_url)

    async def parse_list(self) -> List[Dict[str, Any]]:
        rows = await extract_table_rows(self.page, "table")
        view_links = await self.page.query_selector_all("a:has-text('View')")
        hrefs = [await l.get_attribute("href") for l in view_links]
        items = []
        idx = 0
        for row in rows:
            if len(row) < 8 or not row[0].strip().isdigit():
                continue
            org_lines = row[1].split("\n")
            ref_title_lines = row[2].split("\n")
            tender_id = ref_title_lines[0].strip() if ref_title_lines else None
            reference_no = ref_title_lines[1].strip() if len(ref_title_lines) > 1 else None
            title = ref_title_lines[2].strip() if len(ref_title_lines) > 2 else None
            method_lines = row[3].split("\n")
            date_lines = row[5].split("\n")
            raw_value = row[7].strip()
            href = hrefs[idx] if idx < len(hrefs) else None
            item = {
                "s_no": row[0],
                "ministry": org_lines[0] if len(org_lines) > 0 else None,
                "organization": org_lines[1] if len(org_lines) > 1 else None,
                "pe_name": org_lines[2] if len(org_lines) > 2 else None,
                "tender_id": tender_id,
                "reference_no": reference_no,
                "title": title,
                "procurement_nature": method_lines[0] if method_lines else None,
                "procurement_type": method_lines[1] if len(method_lines) > 1 else None,
                "procurement_method": method_lines[2] if len(method_lines) > 2 else None,
                "district": row[4],
                "advertising_date": date_lines[0] if date_lines else None,
                "noa_date": date_lines[1] if len(date_lines) > 1 else None,
                "contract_awarded_to": row[6],
                "value_raw": raw_value,
                "value_normalized_bdt": normalize_value_bdt(raw_value),
                "detail_href": href,
            }
            if href:
                try:
                    detail_page = await self.context.new_page()
                    url = href if href.startswith("http") else settings.e_gp_base_url + href.lstrip("/")
                    await self.get_navigator(detail_page).goto(url)
                    kv = await extract_label_value_map(detail_page)
                    item["detail_raw"] = kv
                    await detail_page.close()
                    await asyncio.sleep(self.ctx.config.get("rate_limit", 2.0))
                except Exception as e:
                    log.error("offline_award_detail_failed", error=str(e), href=href)
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
