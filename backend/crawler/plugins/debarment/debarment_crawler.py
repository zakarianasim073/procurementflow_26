from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ...framework.config import settings
from ...framework.extractor import extract_table_rows
from ...framework.logger import get_logger
from ...framework.storage import save_raw_record
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.debarment")


@register("debarment")
class DebarmentCrawler(BaseCrawler):
    name = "debarment"
    BASE = "https://www.bppa.gov.bd/debarment/debarment-list.html"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()

    async def parse_list(self) -> List[Dict[str, Any]]:
        all_items = []
        for page_num in range(1, self.ctx.max_pages + 1):
            url = self.BASE if page_num == 1 else f"{self.BASE}?page={page_num}"
            try:
                nav = self.get_navigator(self.page)
                await nav.goto(url)
            except Exception as e:
                log.error("debarment_page_failed", error=str(e), page=page_num)
                break

            rows = await extract_table_rows(self.page, "table")
            found = 0
            for row in rows:
                if len(row) >= 6 and row[0].strip().isdigit():
                    all_items.append({
                        "sl_no": row[0],
                        "firm_company": row[1],
                        "district": row[2],
                        "debar_period": row[3],
                        "debarred_by": row[4],
                        "reasons": row[5],
                    })
                    found += 1

            if found == 0:
                break
            await asyncio.sleep(self.ctx.config.get("rate_limit", 2.0))

        return all_items

    async def next_page(self) -> bool:
        return False

    async def finish(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.browser_manager.release_context(self.context)
