"""X-003 — consume EPDP events, replacing polling. Beat: every 2 min on low queue.

Handlers are deliberately thin: they route into existing machinery (shortlist
task, agent runtime via brain) — no business logic here.
"""

from __future__ import annotations

import asyncio
import logging

from app.celery_app import celery_app
from app.events import EventSubscriber, IncomingEvent

logger = logging.getLogger(__name__)


async def on_opportunity_discovered(event: IncomingEvent) -> None:
    """New opportunity -> incremental shortlist refresh (replaces daily-only)."""
    logger.info("opportunity.discovered %s: %s", event.aggregate_id,
                event.payload.get("title", ""))
    from app.workers.tasks.shortlist_tasks import epdp_daily_shortlist

    epdp_daily_shortlist.apply_async(queue="low")


async def on_workspace_phase_changed(event: IncomingEvent) -> None:
    logger.info("workspace %s: %s -> %s", event.payload.get("workspace_id"),
                event.payload.get("from"), event.payload.get("to"))


async def on_qualification_completed(event: IncomingEvent) -> None:
    logger.info("qualification %s: %s", event.payload.get("workspace_id"),
                event.payload.get("decision"))


async def on_compliance_violation(event: IncomingEvent) -> None:
    logger.warning("compliance violations on %s: %d", event.payload.get("workspace_id"),
                   len(event.payload.get("violations", [])))


def build_subscriber(redis=None) -> EventSubscriber:
    sub = EventSubscriber(redis=redis)
    sub.register("opportunity.discovered", on_opportunity_discovered)
    sub.register("workspace.phase_changed", on_workspace_phase_changed)
    sub.register("qualification.completed", on_qualification_completed)
    sub.register("compliance.violation", on_compliance_violation)
    return sub


@celery_app.task(name="poll_epdp_events", queue="low")
def poll_epdp_events() -> int:
    """Beat entry: one poll pass across all subscribed streams."""
    return asyncio.run(build_subscriber().poll())
