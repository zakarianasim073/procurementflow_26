"""
Webhook Service — Delivery engine with retry, HMAC signing, and audit logging.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import ipaddress
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookSubscription, WebhookDeliveryLog

logger = logging.getLogger(__name__)


async def _validate_webhook_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Webhook URL must be an HTTP(S) URL without embedded credentials")
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("Webhook hostname could not be resolved") from exc
    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Webhook URL resolves to a non-public address")


class WebhookService:
    """
    Deliver events to registered webhook subscribers.

    Features:
    - HMAC-SHA256 signature in X-Webhook-Signature header
    - Automatic retry with exponential backoff
    - Per-subscription circuit breaker (after 10 consecutive failures)
    - Audit logging to webhook_delivery_logs table
    - Async HTTP/2 delivery via httpx
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._http: Optional[httpx.AsyncClient] = None

    async def _http_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=30.0),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
                http2=True,
            )
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # ── CRUD ───────────────────────────────────────────────────────────────

    async def create_subscription(self, tenant_id: Optional[str], url: str,
                                   event_types: List[str], secret: Optional[str] = None,
                                   created_by: Optional[str] = None,
                                   max_retries: int = 3,
                                   retry_interval_seconds: int = 60) -> WebhookSubscription:
        await _validate_webhook_url(url)
        sub = WebhookSubscription(
            tenant_id=tenant_id,
            url=url,
            event_types=event_types,
            secret=secret,
            created_by=created_by,
            max_retries=max_retries,
            retry_interval_seconds=retry_interval_seconds,
        )
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def list_subscriptions(self, tenant_id: Optional[str] = None,
                                  is_active: bool = True,
                                  limit: int = 100) -> List[WebhookSubscription]:
        stmt = select(WebhookSubscription)
        if tenant_id:
            stmt = stmt.where(WebhookSubscription.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(WebhookSubscription.is_active == is_active)
        stmt = stmt.limit(limit).order_by(WebhookSubscription.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_subscription(self, sub_id: str, tenant_id: Optional[str] = None) -> Optional[WebhookSubscription]:
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == sub_id)
        if tenant_id:
            stmt = stmt.where(WebhookSubscription.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_subscription(self, sub_id: str, tenant_id: Optional[str],
                                   **updates) -> Optional[WebhookSubscription]:
        sub = await self.get_subscription(sub_id, tenant_id)
        if not sub:
            return None
        if "url" in updates:
            await _validate_webhook_url(updates["url"])
        for key, value in updates.items():
            if hasattr(sub, key):
                setattr(sub, key, value)
        sub.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return sub

    async def delete_subscription(self, sub_id: str, tenant_id: Optional[str] = None) -> bool:
        sub = await self.get_subscription(sub_id, tenant_id)
        if not sub:
            return False
        await self.session.delete(sub)
        await self.session.flush()
        return True

    # ── Delivery ───────────────────────────────────────────────────────────

    async def deliver(self, event_type: str, payload: Dict[str, Any],
                        event_id: Optional[str] = None,
                        tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Deliver an event to all matching active subscriptions.

        Returns a summary dict with counts.
        """
        subs = await self.list_subscriptions(tenant_id=tenant_id, is_active=True, limit=500)
        matching = [s for s in subs if self._matches_filter(s, event_type, payload)]

        if not matching:
            return {"delivered": 0, "skipped": 0, "matching_subscriptions": 0}

        results = await asyncio.gather(
            *[self._deliver_to_subscription(s, event_type, payload, event_id) for s in matching],
            return_exceptions=True,
        )

        delivered = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))
        errors = sum(1 for r in results if isinstance(r, Exception))

        return {
            "delivered": delivered,
            "failed": failed + errors,
            "matching_subscriptions": len(matching),
            "results": [r if isinstance(r, dict) else str(r) for r in results],
        }

    async def _deliver_to_subscription(self, sub: WebhookSubscription,
                                        event_type: str, payload: Dict[str, Any],
                                        event_id: Optional[str] = None) -> Dict[str, Any]:
        """Deliver a single event to a single subscription with retry."""
        await _validate_webhook_url(sub.url)
        body = json.dumps({
            "event_type": event_type,
            "event_id": event_id or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }, default=str)
        payload_size = len(body.encode("utf-8"))

        signature = ""
        if sub.secret:
            signature = hmac.new(
                sub.secret.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ProcureFlow-Webhook/1.0",
            "X-Webhook-Signature": f"sha256={signature}",
        }

        client = await self._http_client()
        last_error = None
        status_code = None
        response_body = None
        response_time_ms = 0

        for attempt in range(1, sub.max_retries + 1):
            try:
                start = time.time()
                resp = await client.post(sub.url, content=body, headers=headers, follow_redirects=False)
                response_time_ms = int((time.time() - start) * 1000)
                status_code = resp.status_code
                response_body = resp.text[:2000]  # cap audit log

                # Circuit-breaker: deactivate after 10 consecutive failures
                if status_code >= 200 and status_code < 300:
                    sub.success_count += 1
                    sub.failure_count = 0
                    sub.last_status = "success"
                    sub.last_delivered_at = datetime.now(timezone.utc)
                    sub.last_error = None
                    await self._log_delivery(sub, event_type, event_id, payload, payload_size,
                                              status_code, response_body, response_time_ms, attempt, None)
                    await self.session.flush()
                    return {"success": True, "subscription_id": sub.id, "status_code": status_code, "attempt": attempt}
                else:
                    last_error = f"HTTP {status_code}"
                    # Non-2xx is a failure, but we may retry on 5xx or 429
                    if status_code < 500 and status_code != 429:
                        break  # Don't retry 4xx (except 429)

            except Exception as e:
                response_time_ms = int((time.time() - start) * 1000) if 'start' in dir() else 0
                last_error = str(e)
                status_code = None
                response_body = None

            # Retry with backoff
            if attempt < sub.max_retries:
                await asyncio.sleep(sub.retry_interval_seconds * (2 ** (attempt - 1)))

        # All retries exhausted
        sub.failure_count += 1
        sub.last_status = "failed"
        sub.last_error = last_error
        if sub.failure_count >= 10:
            sub.is_active = False
            logger.warning("Webhook subscription %s deactivated after %d failures", sub.id, sub.failure_count)
        await self._log_delivery(sub, event_type, event_id, payload, payload_size,
                                  status_code, response_body, response_time_ms, sub.max_retries, last_error)
        await self.session.flush()
        return {"success": False, "subscription_id": sub.id, "error": last_error, "status_code": status_code}

    async def _log_delivery(self, sub: WebhookSubscription, event_type: str, event_id: Optional[str],
                             payload: Dict, payload_size: int, status_code: Optional[int],
                             response_body: Optional[str], response_time_ms: int,
                             attempt_number: int, error: Optional[str]):
        log = WebhookDeliveryLog(
            subscription_id=sub.id,
            event_type=event_type,
            event_id=event_id,
            payload=payload if payload_size <= 65536 else None,  # Only store small payloads
            payload_size_bytes=payload_size,
            status_code=status_code,
            response_body=response_body,
            response_time_ms=response_time_ms,
            attempt_number=attempt_number,
            error_message=error,
        )
        self.session.add(log)

    # ── Filtering ──────────────────────────────────────────────────────────

    def _matches_filter(self, sub: WebhookSubscription, event_type: str, payload: Dict) -> bool:
        """Check if a subscription should receive this event."""
        if not sub.event_types:
            return True
        # Exact match or wildcard prefix
        for et in sub.event_types:
            if et == event_type or et == "*":
                return True
            if et.endswith(".*") and event_type.startswith(et[:-1]):
                return True
        return False

    # ── Audit ──────────────────────────────────────────────────────────────

    async def get_delivery_logs(self, subscription_id: str, limit: int = 50) -> List[WebhookDeliveryLog]:
        stmt = (
            select(WebhookDeliveryLog)
            .where(WebhookDeliveryLog.subscription_id == subscription_id)
            .order_by(WebhookDeliveryLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def cleanup_old_logs(self, days: int = 30) -> int:
        """Delete delivery logs older than N days."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(WebhookDeliveryLog).where(WebhookDeliveryLog.created_at < cutoff)
        result = await self.session.execute(stmt)
        old_logs = result.scalars().all()
        for log in old_logs:
            await self.session.delete(log)
        await self.session.flush()
        return len(old_logs)


async def publish_webhook_event(
    event_type: str,
    payload: Dict[str, Any],
    *,
    event_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish an outbound webhook event using an owned DB session."""
    from app.db.base import get_session_factory

    async with get_session_factory()() as session:
        svc = WebhookService(session)
        try:
            result = await svc.deliver(event_type=event_type, payload=payload, event_id=event_id, tenant_id=tenant_id)
            await session.commit()
            return result
        finally:
            await svc.close()


def schedule_webhook_event(
    event_type: str,
    payload: Dict[str, Any],
    *,
    event_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """Best-effort background webhook publish for runtime events."""
    async def _run() -> None:
        try:
            await publish_webhook_event(event_type, payload, event_id=event_id, tenant_id=tenant_id)
        except Exception as exc:
            logger.debug("Webhook event publish failed for %s: %s", event_type, exc)

    try:
        asyncio.create_task(_run())
    except RuntimeError:
        logger.debug("Webhook event %s skipped; no running event loop", event_type)
