import pytest

from app.api.v1 import crawl


@pytest.mark.asyncio
async def test_crawl_start_dispatches_celery_without_request_session(monkeypatch):
    class FakeTask:
        id = "crawl-job"

    monkeypatch.setattr(
        "app.workers.tasks.crawl_tasks.run_crawl_import_task.delay",
        lambda crawl_type, max_pages: FakeTask(),
    )

    result = await crawl.start_crawl(crawl_type="tender", max_pages=1)

    assert result == {"run_id": "crawl-job", "status": "started", "type": "tender"}
