import asyncio
import re
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_label_value_map, get_field, extract_table_rows
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()

class APPCrawler(BaseCrawler):
    name = "app"
    START_URL = BASE_URL + "DeptTree.jsp?operation=AdvAPPSearch"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    @with_retry
    async def _goto(self, page, url):
        await page.goto(url, wait_until="networkidle")

    def _pkg_id(self, href: str) -> str:
        m = re.search(r"pkgId=(\d+)", href)
        return m.group(1) if m else ""

    async def run(self, max_pages_per_budget: int = 2):
        self._log_start()
        items_total = 0
        try:
            await self.initialize()
            page = await self.context.new_page()
            await self._goto(page, self.START_URL)

            links = await page.query_selector_all("a")
            budget_links = []
            for link in links:
                href = await link.get_attribute("href")
                text = (await link.inner_text()).strip()
                if href and "StdSearch" in href and text in ("DB", "RB", "OF"):
                    budget_links.append(href)

            for blink in budget_links:
                list_page = await self.context.new_page()
                url = blink if blink.startswith("http") else BASE_URL + blink.lstrip("/")
                await self._goto(list_page, url)

                page_count = 0
                while page_count < max_pages_per_budget:
                    pkg_links = await list_page.query_selector_all("a[href*='ViewPackageDetail']")
                    hrefs = [await l.get_attribute("href") for l in pkg_links]

                    for href in hrefs:
                        if not href:
                            continue
                        try:
                            detail_page = await self.context.new_page()
                            full_url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
                            await self._goto(detail_page, full_url)
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
                                save_raw_record("raw_app_packages", "eprocure_app", data)
                                items_total += 1
                            await detail_page.close()
                            await asyncio.sleep(self.rate_limit)
                        except Exception as e:
                            logger.error("app_item_failed", error=str(e), href=href)

                    self._log_progress(page_count + 1, items_total)
                    next_btn = await list_page.query_selector("a:has-text('Next')")
                    if next_btn:
                        await next_btn.click()
                        await list_page.wait_for_load_state("networkidle")
                        page_count += 1
                    else:
                        break
                await list_page.close()

            self._log_finish("success")
        except Exception as e:
            logger.error("app_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()