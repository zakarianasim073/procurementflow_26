"""X-003 acceptance: idempotency — duplicate delivery causes zero duplicate agent runs."""

from __future__ import annotations

import json
import uuid

import pytest

from app.events import EventSubscriber, IncomingEvent


class FakeRedis:
    """Streams + set subset used by the subscriber."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.groups: dict[tuple[str, str], dict] = {}
        self.sets: dict[str, set] = {}
        self._seq = 0

    async def xadd(self, key, fields, maxlen=None):
        self._seq += 1
        mid = f"{self._seq}-0"
        self.streams.setdefault(key, []).append((mid, dict(fields)))
        return mid

    async def xgroup_create(self, key, group, id="0", mkstream=False):
        if (key, group) in self.groups:
            raise Exception("BUSYGROUP")
        self.streams.setdefault(key, [])
        self.groups[(key, group)] = {"delivered": set(), "acked": set()}

    async def xreadgroup(self, group, consumer, streams, count=20):
        out = []
        for key, start in streams.items():
            g = self.groups[(key, group)]
            entries = self.streams.get(key, [])
            if start == ">":
                batch = [(i, f) for i, f in entries if i not in g["delivered"]][:count]
                g["delivered"].update(i for i, _ in batch)
            else:
                batch = [(i, f) for i, f in entries if i in g["delivered"] and i not in g["acked"]][:count]
            if batch:
                out.append((key, batch))
        return out

    async def xack(self, key, group, mid):
        self.groups[(key, group)]["acked"].add(mid)

    async def sadd(self, key, member):
        s = self.sets.setdefault(key, set())
        if member in s:
            return 0
        s.add(member)
        return 1

    async def srem(self, key, member):
        self.sets.get(key, set()).discard(member)


def _envelope(event_id: str | None = None) -> str:
    return json.dumps({
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": "opportunity.discovered",
        "aggregate_id": "EGP-1",
        "payload": {"title": "Works"},
    })


@pytest.mark.asyncio
async def test_handler_runs_once_per_event():
    redis = FakeRedis()
    runs = []
    sub = EventSubscriber(redis=redis)
    sub.register("opportunity.discovered", lambda e: _record(runs, e))
    await redis.xadd("events:opportunity.discovered", {"data": _envelope()})
    assert await sub.poll() == 1
    assert await sub.poll() == 0
    assert len(runs) == 1


async def _record(runs, event):
    runs.append(event.event_id)


@pytest.mark.asyncio
async def test_duplicate_delivery_zero_duplicate_runs():
    """Same event_id delivered twice (redelivery/replay) -> handler runs once."""
    redis = FakeRedis()
    runs = []
    sub = EventSubscriber(redis=redis)
    sub.register("opportunity.discovered", lambda e: _record(runs, e))

    body = _envelope(event_id="fixed-id")
    await redis.xadd("events:opportunity.discovered", {"data": body})
    await redis.xadd("events:opportunity.discovered", {"data": body})  # duplicate

    handled = await sub.poll()
    assert handled == 1, "duplicate must be ack-skipped"
    assert runs == ["fixed-id"]
    # both stream entries acked - no pending storm
    assert await sub.poll() == 0


@pytest.mark.asyncio
async def test_failed_handler_retries_then_consumer_dlq():
    redis = FakeRedis()
    sub = EventSubscriber(redis=redis)

    async def boom(event):
        raise RuntimeError("bad")

    sub.register("opportunity.discovered", boom)
    await redis.xadd("events:opportunity.discovered", {"data": _envelope()})
    for _ in range(3):
        await sub.poll()
    assert len(redis.streams.get("dlq:opportunity.discovered:procureflow", [])) == 1
    assert await sub.poll() == 0  # acked after DLQ


@pytest.mark.asyncio
async def test_crash_before_ack_redelivers_but_still_one_run():
    """Kill-test + idempotency together: redelivery happens, agent run does not double."""
    redis = FakeRedis()
    runs = []
    sub = EventSubscriber(redis=redis)

    calls = {"n": 0}

    async def crashy(event):
        calls["n"] += 1
        runs.append(event.event_id)
        if calls["n"] == 1:
            raise SystemExit("kill")  # crash AFTER handling started... treated as failure

    sub.register("opportunity.discovered", crashy)
    await redis.xadd("events:opportunity.discovered", {"data": _envelope(event_id="e1")})
    with pytest.raises(SystemExit):
        await sub.poll()

    # restart: pending entry redelivered by transport, but the handler had already
    # claimed e1 (processed set) -> ack-skip, no duplicate agent run
    sub2 = EventSubscriber(redis=redis)
    sub2.register("opportunity.discovered", lambda e: _record(runs, e))
    assert await sub2.poll() == 0
    assert runs == ["e1"]


def test_beat_and_registration():
    from app.celery_app import celery_app

    assert celery_app.conf.beat_schedule["epdp-events-poll"]["task"] == "poll_epdp_events"
    assert "app.workers.tasks.event_tasks" in celery_app.conf.include

    from app.workers.tasks.event_tasks import build_subscriber

    sub = build_subscriber(redis=FakeRedis())
    assert set(sub._handlers) == {
        "opportunity.discovered", "workspace.phase_changed",
        "qualification.completed", "compliance.violation",
    }
