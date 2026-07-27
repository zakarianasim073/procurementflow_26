"""W-011 — Pilot tenant onboarding (idempotent, MOU-gated).

Loads app/data/pilot_tenants.json into the tenants table. Refuses any profile
whose MOU is not signed (charter: signed MOU precedes account creation).

Run:  python -m scripts.onboard_pilot_tenants          (from backend/)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("onboard_pilot_tenants")

DATA_FILE = Path(__file__).resolve().parents[1] / "app" / "data" / "pilot_tenants.json"


def load_gated_tenants() -> list[dict]:
    """MOU gate: returns only signed tenants; raises if any profile is unsigned."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    tenants = data["tenants"]
    unsigned = [t["tenant_id"] for t in tenants if t.get("mou_signed") is not True]
    if unsigned:
        raise PermissionError(
            f"MOU gate: refusing onboarding — unsigned MOU for {unsigned}. "
            "Signed MOU precedes account creation (pilot guardrails)."
        )
    return tenants


async def onboard() -> int:
    from app.db.database import get_async_session

    tenants = load_gated_tenants()
    onboarded = 0
    async with get_async_session() as session:
        for t in tenants:
            await session.execute(
                text(
                    "INSERT INTO tenants (id, name, slug, plan, config, is_active) "
                    "VALUES (:id, :name, :slug, 'pilot', CAST(:config AS json), TRUE) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "name = EXCLUDED.name, config = EXCLUDED.config, plan = 'pilot'"
                ),
                {
                    "id": t["tenant_id"],
                    "name": t["profile"]["company_name"],
                    "slug": t["slug"],
                    "config": json.dumps({"capability_profile": t["profile"], "mou_signed": True}),
                },
            )
            onboarded += 1
            logger.info("onboarded %s (%s)", t["tenant_id"], t["profile"]["company_name"])
        await session.commit()
    return onboarded


if __name__ == "__main__":
    count = asyncio.run(onboard())
    logger.info("done: %d pilot tenants onboarded", count)
    sys.exit(0)


