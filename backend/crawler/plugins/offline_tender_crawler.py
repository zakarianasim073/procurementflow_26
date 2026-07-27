import asyncio
import re
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_table_rows, extract_label_value_map
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()
APP_ID_PATTERN = re.compile(r"APP ID\s*:\s*(\d+)")

class OfflineTenderCrawler(BaseCrawler):
    name = "offline_tender"
    START_URL = BASE_URL + "SearchTenderOffline.jsp"

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
                rows = await extract_table_rows(page, "table")
                view_links = await page.query_selector_all("a:has-text('View')")
                hrefs = [await l.get_attribute("href") for l in view_links]

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
                    data = {
                        "s_no": row[0], "tender_id": tender_id, "reference_no": reference_no,
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
                            url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
                            await self._goto(detail_page, url)
                            kv = await extract_label_value_map(detail_page)
                            data["detail_raw"] = kv
                            await detail_page.close()
                            await asyncio.sleep(self.rate_limit)
                        except Exception as e:
                            logger.error("offline_tender_detail_failed", error=str(e), href=href)

                    save_raw_record("raw_offline_tenders", "eprocure_offline_tender", data)
                    items_total += 1
                    idx += 1

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
            logger.error("offline_tender_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()