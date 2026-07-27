"""
Payments, Team Management, and EGP Alert Filters API Router.
Contains /api/payments/*, /api/team/*, /api/egp-alerts/* endpoints.
"""

import json
import os
import uuid as _uuid_mod
from datetime import datetime, timezone as _tz
from pathlib import Path as _P
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.core.security import get_current_user, get_optional_user
from app.api.v1.helpers import clamp_limit

router = APIRouter()


# ── Pricing / Subscription Endpoints (Stripe) ────────────────────────────

@router.get("/payments/plans")
async def get_pricing_plans():
    """Get available subscription plans."""
    return {
        "success": True,
        "plans": [
            {
                "name": "Free",
                "price": "৳0",
                "period": "/month",
                "description": "For evaluating the platform",
                "features": ["5 Tender Analyses / month", "Basic SOR Comparison", "PDF Export"],
                "plan_name": "free",
            },
            {
                "name": "Professional",
                "price": "৳15,000",
                "period": "/month",
                "description": "For active contractors bidding weekly",
                "features": [
                    "Unlimited Tender Analyses",
                    "PPR 2025 SLT/LERT Engine",
                    "eGP Radar & Alerts",
                    "Competitor Intelligence",
                    "Priority AI Processing",
                ],
                "plan_name": "pro",
                "popular": True,
            },
            {
                "name": "Enterprise",
                "price": "৳45,000",
                "period": "/month",
                "description": "For large firms with multiple estimators",
                "features": [
                    "Everything in Pro",
                    "5 User Seats",
                    "Custom SOR Database",
                    "API Access",
                    "Dedicated Account Manager",
                ],
                "plan_name": "enterprise",
            },
        ],
    }


@router.post("/payments/create-checkout-session")
async def create_checkout_session(
    request: Dict[str, str],
    user: dict = Depends(get_optional_user),
):
    """Create Stripe Checkout Session for subscription."""
    from app.services.payment_service import payment_service

    price_id = request.get("price_id", "")
    plan_name = request.get("plan_name", "")

    if not price_id or not plan_name:
        raise HTTPException(status_code=400, detail="price_id and plan_name required")

    result = await payment_service.create_checkout_session(
        price_id=price_id,
        plan_name=plan_name,
        user_id=user["id"],
        user_email=user.get("email", f"{user['id']}@procureflow.ai"),
    )
    return result


@router.post("/payments/webhook")
async def stripe_webhook(request):
    """Handle Stripe webhook events for subscription lifecycle.

    PUBLIC ENDPOINT: Called by Stripe (external service).
    Authentication: via Stripe signature verification (sig_header).
    """
    from fastapi import Request
    from app.services.payment_service import payment_service

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    result = await payment_service.handle_webhook(payload, sig_header)
    return result


@router.post("/payments/portal")
async def customer_portal(
    user: dict = Depends(get_current_user),
):
    """Create Stripe Customer Portal session for managing subscription."""
    return {
        "success": True,
        "url": "/settings?plan=manage",
        "message": "Stripe Customer Portal URL (configure in production)",
    }


# ── Team Management Endpoints ──────────────────────────────────────────────

_TEAM_DATA_DIR = _P(os.getenv("BOQ_BASE_DIR", str(_P.home() / ".procurementflow-system"))) / "team"
_TEAM_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(name: str) -> list:
    p = _TEAM_DATA_DIR / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _write_json(name: str, data: list):
    (_TEAM_DATA_DIR / name).write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")


@router.get("/team/organizations")
async def list_organizations(user: dict = Depends(get_optional_user)):
    from app.models.enterprise import Organization
    from app.db.base import get_session_factory
    from sqlalchemy import select
    sf = get_session_factory()
    async with sf() as session:
        result = await session.execute(select(Organization))
        orgs = result.scalars().all()
        return {"organizations": [{
            "id": o.id, "name": o.name, "slug": getattr(o, "slug", o.name.lower().replace(" ", "-")),
            "plan": "free", "created_at": str(o.created_at)[:19] if o.created_at else "",
            "member_count": 0,
        } for o in orgs]}


@router.post("/team/organizations")
async def create_organization(data: Dict[str, Any], user: dict = Depends(get_optional_user)):
    from app.models.enterprise import Organization, Tenant
    from app.db.base import get_session_factory
    sf = get_session_factory()
    async with sf() as session:
        try:
            tenant_id = user.get("tenant_id", "") if user else ""
            if not tenant_id:
                tenant = Tenant(name=data.get("name", "New Org"), slug=data.get("name", "new-org").lower().replace(" ", "-"), plan="free")
                session.add(tenant); await session.flush()
                tenant_id = tenant.id
            org = Organization(tenant_id=tenant_id, name=data.get("name", "New Org"), contact_email=user.get("email", "") if user else "")
            session.add(org); await session.flush()
            await session.commit()
            return {"organization": {
                "id": org.id, "name": org.name, "slug": org.name.lower().replace(" ", "-"),
                "plan": "free", "created_at": str(org.created_at)[:19] if org.created_at else "", "member_count": 1,
            }}
        except Exception as e:
            await session.rollback()
            raise HTTPException(400, str(e))


@router.get("/team/organizations/{org_id}/members")
async def list_members(org_id: str, user: dict = Depends(get_optional_user)):
    from app.models.user import User
    from app.db.base import get_session_factory
    from sqlalchemy import select
    sf = get_session_factory()
    async with sf() as session:
        result = await session.execute(select(User).where(User.tenant_id == org_id))
        users = result.scalars().all()
        return {"members": [{
            "user_id": u.id, "email": u.email or "", "name": u.name or u.email or "",
            "role": u.role or "viewer", "status": "active" if u.is_active else "inactive",
            "joined_at": str(u.created_at)[:19] if u.created_at else "",
        } for u in users]}


@router.get("/team/invitations")
async def list_invitations(user: dict = Depends(get_optional_user)):
    return {"invitations": _read_json("invitations.json")}


@router.get("/team/activity")
async def list_activity(
    org_id: str = "",
    limit: int = Query(30, ge=1, le=200),
    user: dict = Depends(get_optional_user),
):
    acts = _read_json("activity.json")
    if org_id:
        acts = [a for a in acts if a.get("org_id") == org_id]
    return {"activity": acts[:clamp_limit(limit, default=30, maximum=200)]}


@router.post("/team/organizations/{org_id}/invite")
async def invite_member(org_id: str, data: Dict[str, Any], user: dict = Depends(get_optional_user)):
    inv = {
        "id": str(_uuid_mod.uuid4()), "org_id": org_id, "email": data.get("email", ""),
        "role": data.get("role", "viewer"), "token": str(_uuid_mod.uuid4()),
        "status": "pending", "invited_by": user.get("email", "") if user else "",
        "created_at": datetime.now(_tz.utc).isoformat(),
        "expires_at": datetime.now(_tz.utc).isoformat().split(".")[0],
    }
    invitations = _read_json("invitations.json")
    invitations.append(inv)
    _write_json("invitations.json", invitations)
    acts = _read_json("activity.json")
    acts.insert(0, {"id": str(_uuid_mod.uuid4()), "org_id": org_id, "action": "invited", "entity_type": "user", "created_at": datetime.now(_tz.utc).isoformat(), "metadata": {"email": data.get("email")}})
    _write_json("activity.json", acts[:200])
    return {"invitation": inv, "invite_link": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/join?token={inv['token']}"}


@router.delete("/team/organizations/{org_id}/members/{user_id}")
async def remove_member(org_id: str, user_id: str, user: dict = Depends(get_optional_user)):
    from app.models.user import User as UserModel
    from app.db.base import get_session_factory
    from sqlalchemy import select
    sf = get_session_factory()
    async with sf() as session:
        try:
            u = (await session.execute(select(UserModel).where(UserModel.id == user_id))).scalars().first()
            if u:
                await session.delete(u)
                await session.commit()
            return {"success": True}
        except Exception as e:
            await session.rollback()
            return {"success": False, "error": str(e)}


# ── EGP Alert Filters Endpoints ────────────────────────────────────────────

_EGP_ALERT_DIR = _P(os.getenv("BOQ_BASE_DIR", str(_P.home() / ".procurementflow-system"))) / "egp_alerts"
_EGP_ALERT_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/egp-alerts/filters")
async def get_egp_alert_filters(user: dict = Depends(get_optional_user)):
    fp = _EGP_ALERT_DIR / "filters.json"
    filters = []
    if fp.exists():
        try:
            filters = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"filters": filters}


@router.post("/egp-alerts/filters")
async def save_egp_alert_filter(data: Dict[str, Any], user: dict = Depends(get_optional_user)):
    fp = _EGP_ALERT_DIR / "filters.json"
    filters = []
    if fp.exists():
        try:
            filters = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not data.get("id"):
        data["id"] = str(_uuid_mod.uuid4())
    filters = [f for f in filters if f.get("id") != data.get("id")]
    filters.append(data)
    fp.write_text(json.dumps(filters, indent=2), encoding="utf-8")
    return {"filters": filters}


@router.delete("/egp-alerts/filters/{filter_id}")
async def delete_egp_alert_filter(filter_id: str, user: dict = Depends(get_optional_user)):
    fp = _EGP_ALERT_DIR / "filters.json"
    filters = []
    if fp.exists():
        try:
            filters = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    filters = [f for f in filters if f.get("id") != filter_id]
    fp.write_text(json.dumps(filters, indent=2), encoding="utf-8")
    return {"success": True}


@router.post("/egp-alerts/poll")
async def poll_egp_alerts(user: dict = Depends(get_optional_user)):
    """Poll for tenders matching saved alert filters."""
    from app.models.tender import Tender, TenderStatus
    from app.db.base import get_session_factory
    from sqlalchemy import select
    fp = _EGP_ALERT_DIR / "filters.json"
    filters = []
    if fp.exists():
        try:
            filters = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    matches = []
    sf = get_session_factory()
    async with sf() as session:
        result = await session.execute(
            select(
                Tender.tender_id, Tender.title, Tender.agency_target,
                Tender.closing_date, Tender.estimated_cost,
            ).where(Tender.status.in_([TenderStatus.LIVE, TenderStatus.ACTIVE])).limit(200)
        )
        for row in result:
            tender_id = row.tender_id or ""
            title = (row.title or "").lower()
            agency = row.agency_target or ""
            closing_date = row.closing_date
            estimated_cost = row.estimated_cost or 0
            for f in filters:
                if not f.get("active", True):
                    continue
                kw = (f.get("keywords", "") or "").lower()
                if kw and kw not in title:
                    continue
                val = float(estimated_cost)
                if f.get("min_value") and val < float(f["min_value"]):
                    continue
                if f.get("max_value") and val > float(f["max_value"]):
                    continue
                matches.append({
                    "tender_id": tender_id,
                    "title": row.title or "",
                    "department": agency or "",
                    "deadline": str(closing_date)[:10] if closing_date else "",
                    "estimated_value": val,
                    "matched_keywords": [kw] if kw else [],
                })
                break
    return {"matches": matches}
