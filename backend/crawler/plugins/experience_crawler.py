import asyncio
import re
import structlog
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import extract_table_rows
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL
from backend.crawler.framework.retry import with_retry

logger = structlog.get_logger()
CERT_PATTERN = re.compile(r"^(.*?)/(eTenders|eCMS|Manual)/(\d{8})/(\d+)$")

def parse_cert_no(cert_no: str) -> dict:
    if not cert_no:
        return {"package_reference": None, "source_type": None, "cert_date": None, "cert_serial": None}
    m = CERT_PATTERN.match(cert_no.strip())
    if not m:
        return {"package_reference": cert_no, "source_type": None, "cert_date": None, "cert_serial": None}
    return {
        "package_reference": m.group(1).strip(), "source_type": m.group(2),
        "cert_date": m.group(3), "cert_serial": m.group(4),
    }

class ExperienceCrawler(BaseCrawler):
    name = "experience"
    START_URL = BASE_URL + "SearcheCMS.jsp?tab=All"

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
                found = 0
                for row in rows:
                    if len(row) < 9 or not row[0].strip().isdigit():
                        continue
                    org_lines = row[1].split("\n")
                    nature_lines = row[2].split("\n")
                    cert_info = parse_cert_no(row[6])
                    data = {
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
                    }
                    save_raw_record("raw_experience", "eprocure_experience", data)
                    items_total += 1
                    found += 1

                self._log_progress(page_count + 1, items_total)
                if found == 0:
                    break
                next_btn = await page.query_selector("a:has-text('Next')")
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle")
                    page_count += 1
                    await asyncio.sleep(self.rate_limit)
                else:
                    break

            self._log_finish("success")
        except Exception as e:
            logger.error("experience_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()