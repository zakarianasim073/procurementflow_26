import asyncio
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_label_value_map, get_field, extract_table_rows
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()

class AwardCrawler(BaseCrawler):
    name = "award"
    START_URL = BASE_URL + "SearchNOA.jsp"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    @with_retry
    async def _goto(self, page, url):
        await page.goto(url, wait_until="networkidle")

    async def run(self, max_pages: int = 3):
        self._log_start()
        items_total = 0
        try:
            await self.initialize()
            page = await self.context.new_page()
            await self._goto(page, self.START_URL)

            page_count = 0
            while page_count < max_pages:
                links = await page.query_selector_all("a")
                hrefs = []
                for link in links:
                    href = await link.get_attribute("href")
                    if href and "ViewAwardedContracts" in href:
                        hrefs.append(href)

                for href in hrefs:
                    try:
                        detail_page = await self.context.new_page()
                        url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
                        await self._goto(detail_page, url)
                        kv = await extract_label_value_map(detail_page)
                        bo_rows = await extract_table_rows(detail_page, "table")
                        owners = [
                            {"name": r[1], "ownership_pct": r[2], "country": r[3] if len(r) > 3 else None}
                            for r in bo_rows if len(r) >= 3 and r[0].strip().isdigit()
                        ]
                        data = {
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
                            "beneficial_owners": owners,
                            "raw": kv,
                        }
                        if data.get("tender_id"):
                            save_raw_record("raw_awards", "eprocure_award", data)
                            items_total += 1
                        await detail_page.close()
                        await asyncio.sleep(self.rate_limit)
                    except Exception as e:
                        logger.error("award_item_failed", error=str(e), href=href)

                self._log_progress(page_count + 1, items_total)
                next_btn = await page.query_selector("a:has-text('Next')")
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle")
                    page_count += 1
                else:
                    break

            self._log_finish("success")
        except Exception as e:
            logger.error("award_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()