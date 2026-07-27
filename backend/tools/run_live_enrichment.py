"""Isolated worker for durable live-tender enrichment queue entries."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.api.v1.tender_processing import process_tender_with_agents
from app.db.base import get_session_factory
from app.models.intelligence import KnowledgeEntry


async def process_entry(entry_id: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as db:
        entry = await db.get(KnowledgeEntry, entry_id)
        if not entry:
            return
        payload = dict(entry.data or {})
        payload.update({"status": "running", "started_at": datetime.now(timezone.utc).isoformat(), "error": None})
        entry.data = payload
        await db.commit()
        tender_id = str(entry.tender_id or "")

    try:
        async with session_factory() as db:
            result = await process_tender_with_agents(
                tender_id=tender_id,
                sor_agency="BWDB",
                zone=None,
                run_live_acquisition=True,
                full_pipeline=False,
                db=db,
            )
        async with session_factory() as db:
            entry = await db.get(KnowledgeEntry, entry_id)
            requirement = (
                await db.execute(
                    select(KnowledgeEntry)
                    .where(
                        KnowledgeEntry.tender_id == tender_id,
                        KnowledgeEntry.entry_type == "tender_requirement_enrichment",
                        KnowledgeEntry.is_archived.is_(False),
                    )
                    .order_by(KnowledgeEntry.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            req_data = requirement.data if requirement and isinstance(requirement.data, dict) else {}
            req_payload = req_data.get("payload", req_data)
            requirements = req_payload.get("requirements", []) if isinstance(req_payload, dict) else []
            if entry:
                payload = dict(entry.data or {})
                payload.update({
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "requirements_count": len(requirements) if isinstance(requirements, list) else 0,
                    "tender_security_text": req_payload.get("tender_security_text") if isinstance(req_payload, dict) else None,
                    "pipeline_status": result.get("status") if isinstance(result, dict) else "completed",
                    "error": None,
                })
                entry.data = payload
                await db.commit()
    except Exception as exc:
        async with session_factory() as db:
            entry = await db.get(KnowledgeEntry, entry_id)
            if entry:
                payload = dict(entry.data or {})
                payload.update({
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc)[:1000],
                })
                entry.data = payload
                await db.commit()


async def main() -> None:
    for entry_id in sys.argv[1:]:
        await process_entry(entry_id)


if __name__ == "__main__":
    asyncio.run(main())
