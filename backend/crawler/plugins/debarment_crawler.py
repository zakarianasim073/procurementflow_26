import asyncio
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_table_rows
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()

class DebarmentCrawler(BaseCrawler):
    name = "debarment"
    BASE = "https://www.bppa.gov.bd/debarment/debarment-list.html"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    @with_retry
    async def _goto(self, page, url):
        await page.goto(url, wait_until="networkidle")

    async def run(self, max_pages: int = 5):
        self._log_start()
        items_total = 0
        try:
            await self.initialize()
            page = await self.context.new_page()

            for page_num in range(1, max_pages + 1):
                url = self.BASE if page_num == 1 else f"{self.BASE}?page={page_num}"
                try:
                    await self._goto(page, url)
                except Exception as e:
                    logger.error("debarment_page_failed", error=str(e), page=page_num)
                    break

                rows = await extract_table_rows(page, "table")
                found = 0
                for row in rows:
                    if len(row) >= 6 and row[0].strip().isdigit():
                        data = {
                            "sl_no": row[0], "firm_company": row[1], "district": row[2],
                            "debar_period": row[3], "debarred_by": row[4], "reasons": row[5],
                        }
                        save_raw_record("raw_debarment", "bppa_debarment", data)
                        items_total += 1
                        found += 1

                self._log_progress(page_num, items_total)
                if found == 0:
                    break
                await asyncio.sleep(self.rate_limit)

            self._log_finish("success")
        except Exception as e:
            logger.error("debarment_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()