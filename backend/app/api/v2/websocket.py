"""WebSocket/SSE endpoints for real-time updates (T-038).

Provides:
- WebSocket /ws/crawl/status — crawl progress events
- WebSocket /ws/agent/run — AI agent execution streaming
- SSE /events/metrics — live dashboard metrics
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

ws_router = APIRouter(prefix="", tags=["websocket"])
sse_router = APIRouter(prefix="", tags=["sse"])

_active_connections: dict[str, list[WebSocket]] = {}
_crawl_status: dict = {}
_agent_streams: dict = {}
_metrics_cache: dict = {}
_metrics_cache_ts: float = 0.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@ws_router.websocket("/crawl/status")
async def ws_crawl_status(websocket: WebSocket):
    """WebSocket for real-time crawl progress."""
    await websocket.accept()
    conn_list = _active_connections.setdefault("crawl", [])
    conn_list.append(websocket)
    try:
        if _crawl_status:
            await websocket.send_json({
                "type": "crawl_status",
                "data": _crawl_status,
                "ts": _now_iso(),
            })
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "ts": _now_iso()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in conn_list:
            conn_list.remove(websocket)


@ws_router.websocket("/agent/run")
async def ws_agent_run(websocket: WebSocket):
    """WebSocket for streaming AI agent execution results."""
    await websocket.accept()
    conn_list = _active_connections.setdefault("agent", [])
    conn_list.append(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                agent_id = data.get("agent_id", "")
                if data.get("action") == "subscribe":
                    _agent_streams[websocket] = agent_id
                    await websocket.send_json({
                        "type": "subscribed",
                        "agent_id": agent_id,
                        "ts": _now_iso(),
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in conn_list:
            conn_list.remove(websocket)
        _agent_streams.pop(websocket, None)


@sse_router.get("/metrics/stream")
async def sse_metrics(
    last_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """SSE endpoint for live metrics updates."""
    async def event_generator():
        while True:
            now_ts = datetime.now(timezone.utc).timestamp()
            global _metrics_cache_ts
            if now_ts - _metrics_cache_ts > 30:
                try:
                    from sqlalchemy import func
                    from app.models.tender import Tender
                    from app.models.award_records_v2 import AwardRecordV2

                    total_tenders = (await db.execute(
                        select(func.count(Tender.id))
                    )).scalar() or 0
                    total_awards = (await db.execute(
                        select(func.count(AwardRecordV2.id))
                    )).scalar() or 0

                    _metrics_cache = {
                        "total_tenders": total_tenders,
                        "total_awards": total_awards,
                        "active_agents": 0,
                    }
                    _metrics_cache_ts = now_ts
                except Exception:
                    pass

            event = json.dumps({
                "type": "metrics",
                "data": _metrics_cache,
                "ts": _now_iso(),
            })
            yield f"data: {event}\n\n"
            await asyncio.sleep(5)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def publish_crawl_update(data: dict) -> None:
    """Publish crawl progress to all connected crawl WebSocket clients."""
    global _crawl_status
    _crawl_status = data
    for ws in list(_active_connections.get("crawl", [])):
        try:
            await ws.send_json({
                "type": "crawl_update",
                "data": data,
                "ts": _now_iso(),
            })
        except Exception:
            pass


async def publish_agent_result(agent_id: str, result: dict) -> None:
    """Publish agent execution result to subscribed WebSocket clients."""
    for ws, subscribed_agent in list(_agent_streams.items()):
        if subscribed_agent == agent_id or subscribed_agent == "*":
            try:
                await ws.send_json({
                    "type": "agent_result",
                    "agent_id": agent_id,
                    "data": result,
                    "ts": _now_iso(),
                })
            except Exception:
                pass
