import asyncio
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_table_rows, extract_label_value_map
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()

def normalize_value_bdt(raw_value: str) -> float:
    try:
        val = float(raw_value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
    if val < 1000:
        return val * 10_000_000
    return val

class OfflineAwardCrawler(BaseCrawler):
    name = "offline_award"
    START_URL = BASE_URL + "SearchAwardedContractOffline.jsp"

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
                    data = {
                        "s_no": row[0],
                        "ministry": org_lines[0] if len(org_lines) > 0 else None,
                        "organization": org_lines[1] if len(org_lines) > 1 else None,
                        "pe_name": org_lines[2] if len(org_lines) > 2 else None,
                        "tender_id": tender_id, "reference_no": reference_no, "title": title,
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
                            url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
                            await self._goto(detail_page, url)
                            kv = await extract_label_value_map(detail_page)
                            data["detail_raw"] = kv
                            await detail_page.close()
                            await asyncio.sleep(self.rate_limit)
                        except Exception as e:
                            logger.error("offline_award_detail_failed", error=str(e), href=href)

                    save_raw_record("raw_offline_awards", "eprocure_offline_award", data)
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
            logger.error("offline_award_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()