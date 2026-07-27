"""
Webhook API Router — CRUD + manual delivery trigger.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user, get_optional_user
from app.db.base import get_async_session
from app.services.webhook_service import WebhookService
from app.api.v1.helpers import clamp_limit

logger = logging.getLogger("procureflow")
router = APIRouter()


class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(..., min_length=10, max_length=2048)
    event_types: List[str] = Field(default=["*"])
    secret: Optional[str] = Field(default=None, max_length=255)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_interval_seconds: int = Field(default=60, ge=1, le=3600)


class WebhookSubscriptionUpdate(BaseModel):
    url: Optional[str] = None
    event_types: Optional[List[str]] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None
    max_retries: Optional[int] = None
    retry_interval_seconds: Optional[int] = None


class WebhookDeliverRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any] = {}
    event_id: Optional[str] = None


# ── CRUD Endpoints ───────────────────────────────────────────────────────

@router.get("/webhooks")
async def list_webhooks(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """List all webhook subscriptions for the current tenant."""
    svc = WebhookService(db)
    tenant_id = user.get("tenant_id")
    subs = await svc.list_subscriptions(
        tenant_id=tenant_id,
        is_active=None,
        limit=clamp_limit(limit, default=50, maximum=200),
    )
    return {
        "success": True,
        "subscriptions": [s.to_dict() for s in subs],
    }


@router.post("/webhooks")
async def create_webhook(req: WebhookSubscriptionCreate,
                          user: dict = Depends(get_current_user),
                          db=Depends(get_async_session)):
    """Register a new webhook subscription."""
    svc = WebhookService(db)
    sub = await svc.create_subscription(
        tenant_id=user.get("tenant_id"),
        url=req.url,
        event_types=req.event_types,
        secret=req.secret,
        created_by=user.get("id"),
        max_retries=req.max_retries,
        retry_interval_seconds=req.retry_interval_seconds,
    )
    await db.commit()
    return {"success": True, "subscription": sub.to_dict()}


@router.get("/webhooks/{sub_id}")
async def get_webhook(sub_id: str,
                       user: dict = Depends(get_current_user),
                       db=Depends(get_async_session)):
    """Get a single webhook subscription."""
    svc = WebhookService(db)
    sub = await svc.get_subscription(sub_id, tenant_id=user.get("tenant_id"))
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"success": True, "subscription": sub.to_dict()}


@router.put("/webhooks/{sub_id}")
async def update_webhook(sub_id: str,
                          req: WebhookSubscriptionUpdate,
                          user: dict = Depends(get_current_user),
                          db=Depends(get_async_session)):
    """Update a webhook subscription."""
    svc = WebhookService(db)
    updates = req.model_dump(exclude_unset=True)
    sub = await svc.update_subscription(sub_id, user.get("tenant_id"), **updates)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.commit()
    return {"success": True, "subscription": sub.to_dict()}


@router.delete("/webhooks/{sub_id}")
async def delete_webhook(sub_id: str,
                          user: dict = Depends(get_current_user),
                          db=Depends(get_async_session)):
    """Delete a webhook subscription."""
    svc = WebhookService(db)
    ok = await svc.delete_subscription(sub_id, tenant_id=user.get("tenant_id"))
    if not ok:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.commit()
    return {"success": True, "message": "Webhook deleted"}


# ── Delivery Endpoints ───────────────────────────────────────────────────

@router.post("/webhooks/{sub_id}/deliver")
async def deliver_to_webhook(sub_id: str,
                              req: WebhookDeliverRequest,
                              user: dict = Depends(get_current_user),
                              db=Depends(get_async_session)):
    """Manually trigger delivery to a specific webhook."""
    svc = WebhookService(db)
    sub = await svc.get_subscription(sub_id, tenant_id=user.get("tenant_id"))
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    result = await svc._deliver_to_subscription(sub, req.event_type, req.payload, req.event_id)
    await db.commit()
    return {"success": result.get("success"), **result}


@router.post("/webhooks/deliver")
async def deliver_event(req: WebhookDeliverRequest,
                         user: dict = Depends(get_current_user),
                         db=Depends(get_async_session)):
    """Broadcast an event to all matching webhooks."""
    svc = WebhookService(db)
    result = await svc.deliver(
        event_type=req.event_type,
        payload=req.payload,
        event_id=req.event_id,
        tenant_id=user.get("tenant_id"),
    )
    await db.commit()
    return {"success": True, **result}


# ── Audit Logs ───────────────────────────────────────────────────────────

@router.get("/webhooks/{sub_id}/logs")
async def get_webhook_logs(sub_id: str,
                            limit: int = Query(50, ge=1, le=500),
                            user: dict = Depends(get_current_user),
                            db=Depends(get_async_session)):
    """Get delivery logs for a webhook."""
    svc = WebhookService(db)
    sub = await svc.get_subscription(sub_id, tenant_id=user.get("tenant_id"))
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    logs = await svc.get_delivery_logs(sub_id, limit=clamp_limit(limit, default=50, maximum=500))
    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "event_id": log.event_id,
                "status_code": log.status_code,
                "response_time_ms": log.response_time_ms,
                "attempt_number": log.attempt_number,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
