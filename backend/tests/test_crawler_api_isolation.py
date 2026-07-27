import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.api.v1 import crawler


@pytest.mark.asyncio
async def test_app_listing_crawl_runs_off_event_loop(monkeypatch):
    calls = []

    async def fake_to_thread(func, **kwargs):
        calls.append((func, kwargs))
        return {"2025-2026": 2}

    monkeypatch.setattr(crawler.asyncio, "to_thread", fake_to_thread)

    result = await crawler.crawl_app_listings(
        start_fy="2025-2026",
        max_pages=1,
        fys=None,
    )

    assert calls
    assert result["total_records"] == 2
