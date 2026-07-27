import asyncio
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_label_value_map, get_field
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()

class TenderCrawler(BaseCrawler):
    name = "tender"
    START_URL = BASE_URL + "AllTenders.jsp?h=t"

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
                rows = await page.query_selector_all("table tr")
                links = []
                for row in rows:
                    link = await row.query_selector("a")
                    if link:
                        href = await link.get_attribute("href")
                        if href and "ViewTender" in href:
                            links.append(href)

                for href in links:
                    try:
                        detail_page = await self.context.new_page()
                        url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
                        await self._goto(detail_page, url)
                        kv = await extract_label_value_map(detail_page)
                        data = {
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
                            "raw": kv,
                        }
                        if data.get("tender_id"):
                            save_raw_record("raw_tenders", "eprocure_tender", data)
                            items_total += 1
                        await detail_page.close()
                        await asyncio.sleep(self.rate_limit)
                    except Exception as e:
                        logger.error("tender_item_failed", error=str(e), href=href)

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
            logger.error("tender_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()