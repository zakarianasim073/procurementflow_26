"""W-003 wiring — daily per-firm shortlist via EPDP /v1/tender/shortlist.

ProcureFlow owns firm profiles and the schedule; EPDP owns opportunities and
the filter engine. This task ships profiles to EPDP and logs each firm's
shortlist size (data-wall: results handled strictly per firm).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

PROFILES_FILE = Path(__file__).resolve().parents[3] / "app" / "data" / "pilot_tenants.json"


def _load_profiles() -> list[dict[str, Any]]:
    """Pilot capability profiles → EPDP FirmCapabilityProfile shape."""
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles = []
    for tenant in data["tenants"]:
        p = tenant["profile"]
        profiles.append(
            {
                "firm_id": tenant["tenant_id"],
                "preferred_agencies": p.get("preferred_agencies", []),
                "districts": p.get("districts", []),
                "categories": ["Works"],
                "avg_turnover": p.get("avg_turnover", 0),
            }
        )
    return profiles


async def _run_shortlist() -> dict[str, int]:
    from app.clients.epdp import EPDPClient

    profiles = _load_profiles()
    async with EPDPClient() as client:
        results = await client.shortlist(profiles)
    sizes = {r.firm_id: len(r.entries) for r in results}
    for firm_id, count in sizes.items():
        logger.info("daily shortlist: %s -> %d opportunities", firm_id, count)
    return sizes


@celery_app.task(name="epdp_daily_shortlist", queue="low")
def epdp_daily_shortlist() -> dict[str, int]:
    """Beat entry point (see celery_app.conf.beat_schedule)."""
    return asyncio.run(_run_shortlist())
