from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from ...framework.config import settings
from ...framework.extractor import extract_table_rows
from ...framework.logger import get_logger
from ...framework.storage import save_raw_record
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.experience")

CERT_PATTERN = re.compile(r"^(.*?)/(eTenders|eCMS|Manual)/(\d{8})/(\d+)$")


def parse_cert_no(cert_no: str) -> dict:
    if not cert_no:
        return {"package_reference": None, "source_type": None, "cert_date": None, "cert_serial": None}
    m = CERT_PATTERN.match(cert_no.strip())
    if not m:
        return {"package_reference": cert_no, "source_type": None, "cert_date": None, "cert_serial": None}
    return {
        "package_reference": m.group(1).strip(),
        "source_type": m.group(2),
        "cert_date": m.group(3),
        "cert_serial": m.group(4),
    }


@register("experience")
class ExperienceCrawler(BaseCrawler):
    name = "experience"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    async def search(self):
        self.page = await self.context.new_page()
        nav = self.get_navigator(self.page)
        start_url = settings.url("SearcheCMS.jsp?tab=All")
        await nav.goto(start_url)

    async def parse_list(self) -> List[Dict[str, Any]]:
        rows = await extract_table_rows(self.page, "table")
        items = []
        for row in rows:
            if len(row) >= 9 and row[0].strip().isdigit():
                org_lines = row[1].split("\n")
                nature_lines = row[2].split("\n")
                cert_info = parse_cert_no(row[6])
                items.append({
                    "s_no": row[0],
                    "ministry": org_lines[0] if len(org_lines) > 0 else None,
                    "division": org_lines[1] if len(org_lines) > 1 else None,
                    "organization": org_lines[2] if len(org_lines) > 2 else None,
                    "pe_office": org_lines[3] if len(org_lines) > 3 else None,
                    "procurement_nature": nature_lines[0] if len(nature_lines) > 0 else None,
                    "procurement_type": nature_lines[1] if len(nature_lines) > 1 else None,
                    "procurement_method": nature_lines[2] if len(nature_lines) > 2 else None,
                    "title": row[3],
                    "contract_awarded_to": row[4],
                    "company_unique_id": row[5],
                    "experience_cert_no": row[6],
                    "package_reference": cert_info["package_reference"],
                    "source_type": cert_info["source_type"],
                    "contract_amount_bdt": row[7],
                    "contract_dates": row[8],
                    "work_status": row[9] if len(row) > 9 else None,
                })
        return items

    async def next_page(self) -> bool:
        next_btn = await self.page.query_selector("a:has-text('Next')")
        if next_btn:
            await next_btn.click()
            await self.get_navigator(self.page).wait_ready()
            await asyncio.sleep(self.ctx.config.get("rate_limit", 2.0))
            return True
        return False

    async def finish(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.browser_manager.release_context(self.context)
