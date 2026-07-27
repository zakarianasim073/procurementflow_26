from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.celery_app import celery_app


@celery_app.task(name="run_crawl_import_task")
def run_crawl_import_task(crawl_type: str, max_pages: int = 50) -> Dict[str, Any]:
    return asyncio.run(_run_crawl(crawl_type, max_pages))


async def _run_crawl(crawl_type: str, max_pages: int) -> Dict[str, Any]:
    from app.db.database import get_async_session
    from app.services.crawl_import_service import CrawlImportService

    async with get_async_session() as session:
        service = CrawlImportService(session)
        operations = {
            "all": service.crawl_and_import_all,
            "app": service.crawl_app_listings,
            "tender": service.crawl_live_tenders,
            "award": service.crawl_awards,
            "documents": service.crawl_documents,
            "experience": service.crawl_experience,
            "debarment": service.crawl_debarment,
        }
        result = await operations[crawl_type](max_pages=max_pages)
        return {"type": crawl_type, **result}
