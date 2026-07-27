"""
Communication, Notification, and Alert API Router.
Contains /api/alerts/*, /api/settings/smtp/*, /api/whatsapp/*, /api/openclaw/* endpoints.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.api.v1.helpers import clamp_limit, load_tender_snapshot
from app.core.security import get_current_user, get_optional_user

logger = logging.getLogger("procureflow")
router = APIRouter()


# ── Alert Endpoints ─────────────────────────────────────────────────────

from app.services.notification_service import notification_service, TenderAlert


@router.get("/alerts")
async def get_alerts(limit: int = Query(20, ge=1, le=200), alert_type: str = None):
    """Get recent tender alerts."""
    limit = clamp_limit(limit, default=20, maximum=200)
    alerts = notification_service.get_alerts(limit=limit, alert_type=alert_type)
    return {"success": True, "total": len(alerts), "alerts": alerts}


@router.delete("/alerts/clear")
async def clear_alerts(older_than_days: int = 30, user: dict = Depends(get_current_user)):
    """Clear old alerts."""
    cleared = notification_service.clear_alerts(older_than_days=older_than_days)
    return {"success": True, "cleared": cleared}


@router.post("/alerts/test-email")
async def test_email_alert(request: Dict[str, str], user: dict = Depends(get_current_user)):
    """Send a test email alert."""
    email = request.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    alert = TenderAlert(
        tender_id="TEST-001",
        title="Test Alert from Procurement Flow Specialist BD",
        procuring_entity="Test Entity",
        match_score=0.95,
        estimated_value=10_000_000,
        deadline="2026-07-01",
        alert_type="new_tender",
    )

    sent = notification_service.send_tender_alert_email(email, alert)
    return {"success": sent, "message": "Test email sent" if sent else "Email not configured"}


# ── SMTP Settings Endpoints ───────────────────────────────────────────────

class SMTPSettings(BaseModel):
    smtp_host: str = None
    smtp_port: int = None
    smtp_user: str = None
    smtp_pass: str = None
    smtp_from: str = None
    alert_email: str = None


@router.get("/settings/smtp")
async def get_smtp_settings(user: dict = Depends(get_current_user)):
    """Get current SMTP config (password masked)."""
    from app.services.notification_service import notification_service
    ns = notification_service
    return {
        "smtp_host": ns.smtp_host or os.getenv("SMTP_HOST", ""),
        "smtp_port": ns.smtp_port or int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": ns.smtp_user or os.getenv("SMTP_USER", ""),
        "smtp_pass": "••••••••" if (ns.smtp_pass or os.getenv("SMTP_PASS", "")) else "",
        "smtp_from": ns.from_email or os.getenv("NOTIFICATION_FROM", "alerts@procureflow.ai"),
        "alert_email": os.getenv("ALERT_EMAIL", ""),
        "configured": bool(ns.smtp_host and ns.smtp_pass) or bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_PASS")),
    }


@router.post("/settings/smtp")
async def update_smtp_settings(settings: SMTPSettings, user: dict = Depends(get_current_user)):
    """Update SMTP configuration (in-memory for current session)."""
    from app.services.notification_service import notification_service
    ns = notification_service

    if settings.smtp_host is not None:
        ns.smtp_host = settings.smtp_host
        os.environ["SMTP_HOST"] = settings.smtp_host
    if settings.smtp_port is not None:
        ns.smtp_port = settings.smtp_port
        os.environ["SMTP_PORT"] = str(settings.smtp_port)
    if settings.smtp_user is not None:
        ns.smtp_user = settings.smtp_user
        os.environ["SMTP_USER"] = settings.smtp_user
    if settings.smtp_pass is not None:
        ns.smtp_pass = settings.smtp_pass
        os.environ["SMTP_PASS"] = settings.smtp_pass
    if settings.smtp_from is not None:
        ns.from_email = settings.smtp_from
    if settings.alert_email is not None:
        os.environ["ALERT_EMAIL"] = settings.alert_email

    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            updated_keys = set()
            for line in lines:
                stripped = line.strip()
                key_updated = False
                for key, val in [
                    ("SMTP_HOST", settings.smtp_host),
                    ("SMTP_PORT", str(settings.smtp_port) if settings.smtp_port else None),
                    ("SMTP_USER", settings.smtp_user),
                    ("SMTP_PASS", settings.smtp_pass),
                ]:
                    if val is not None and stripped.startswith(f"{key}="):
                        new_lines.append(f"{key}={val}")
                        updated_keys.add(key)
                        key_updated = True
                        break
                if not key_updated:
                    new_lines.append(line)
            for key, val in [
                ("SMTP_HOST", settings.smtp_host),
                ("SMTP_PORT", str(settings.smtp_port) if settings.smtp_port else None),
                ("SMTP_USER", settings.smtp_user),
                ("SMTP_PASS", settings.smtp_pass),
                ("ALERT_EMAIL", settings.alert_email),
            ]:
                if val is not None and key not in updated_keys and key != "SMTP_PORT":
                    new_lines.append(f"{key}={val}")
                    updated_keys.add(key)
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not persist .env: {e}")

    return {"success": True, "message": "SMTP settings updated"}


class TestEmailRequest(BaseModel):
    email: str


@router.post("/settings/smtp/test")
async def test_smtp_settings(req: TestEmailRequest, user: dict = Depends(get_current_user)):
    """Send a test email using current SMTP settings."""
    from app.services.notification_service import notification_service
    ns = notification_service

    if not ns.smtp_host:
        return {"success": False, "message": "SMTP not configured — set host and credentials first"}
    if not ns.smtp_pass:
        return {"success": False, "message": "SMTP password (App Password) not set"}

    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(
            "<html><body><h2>Procurement Flow — Test Email</h2>"
            "<p>Your SMTP/Gmail App Password configuration is working!</p>"
            "<hr><p style='color:#666;font-size:12px'>Procurement Flow Specialist BD</p>"
            "</body></html>",
            "html",
        )
        msg["Subject"] = "Procurement Flow — SMTP Test Successful"
        msg["From"] = ns.from_email
        msg["To"] = req.email

        with smtplib.SMTP(ns.smtp_host, int(ns.smtp_port or 587)) as server:
            server.starttls()
            server.login(ns.smtp_user, ns.smtp_pass)
            server.send_message(msg)

        return {"success": True, "message": f"Test email sent to {req.email}"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Authentication failed. Use a 16-char Gmail App Password (not your regular password). Generate one at https://myaccount.google.com/apppasswords"}
    except smtplib.SMTPException as e:
        return {"success": False, "message": f"SMTP error: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Failed: {e}"}


# ── WhatsApp Notification Endpoints ────────────────────────────────────

@router.get("/whatsapp/settings")
async def get_whatsapp_settings(user: dict = Depends(get_current_user)):
    """Get WhatsApp configuration."""
    from app.services.whatsapp_service import whatsapp_service
    phone = os.getenv("WHATSAPP_PHONE", whatsapp_service.default_phone)
    return {
        "phone": phone,
        "configured": bool(phone),
    }


@router.post("/whatsapp/settings")
async def update_whatsapp_settings(req: Dict[str, str], user: dict = Depends(get_current_user)):
    """Update WhatsApp phone number."""
    phone = req.get("phone", "")
    if phone:
        os.environ["WHATSAPP_PHONE"] = phone
        from app.services.whatsapp_service import whatsapp_service
        whatsapp_service.default_phone = phone
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        if env_path.exists():
            try:
                lines = env_path.read_text(encoding="utf-8").splitlines()
                found = False
                new_lines = []
                for line in lines:
                    if line.strip().startswith("WHATSAPP_PHONE="):
                        new_lines.append(f"WHATSAPP_PHONE={phone}")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"\n# WhatsApp\nWHATSAPP_PHONE={phone}")
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not persist WhatsApp phone: {e}")
    return {"success": True, "phone": phone}


class WhatsAppTenderRequest(BaseModel):
    tender_id: str = ""
    phone: str = ""
    language: str = "bn"


@router.post("/whatsapp/share-tender")
async def share_tender_via_whatsapp(req: WhatsAppTenderRequest):
    """Generate WhatsApp share link for a tender."""
    from app.services.whatsapp_service import whatsapp_service

    tender = await load_tender_snapshot(req.tender_id) if req.tender_id else None

    if not tender:
        tender = {"tender_id": req.tender_id or "unknown", "title": "", "procuring_entity": ""}

    link = whatsapp_service.get_tender_wa_link(tender, phone=req.phone, lang=req.language)
    msg = whatsapp_service.format_tender_alert(tender, lang=req.language)
    return {
        "success": True,
        "wa_link": link,
        "message": msg,
        "phone": req.phone or whatsapp_service.default_phone,
    }


@router.post("/whatsapp/share-summary")
async def share_summary_via_whatsapp(req: Dict[str, Any]):
    """Generate WhatsApp share link for a summary of tenders."""
    from app.services.whatsapp_service import whatsapp_service
    tenders = req.get("tenders", [])
    phone = req.get("phone", "")
    lang = req.get("language", "bn")

    link = whatsapp_service.get_summary_wa_link(tenders, phone=phone, lang=lang)
    msg = whatsapp_service.format_summary(tenders, lang=lang)
    return {
        "success": True,
        "wa_link": link,
        "message": msg,
        "count": len(tenders),
    }


@router.get("/whatsapp/alerts")
async def get_whatsapp_alerts(limit: int = Query(20, ge=1, le=200)):
    """Get recent WhatsApp alerts."""
    from app.services.whatsapp_service import whatsapp_service
    limit = clamp_limit(limit, default=20, maximum=200)
    alerts = whatsapp_service.get_recent_alerts(limit=limit)
    return {"success": True, "alerts": alerts}


# ── WhatsApp Automation with OpenClaw ─────────────────────────────────

class WhatsAppSendRequest(BaseModel):
    phone: str = ""
    message: str = ""
    tender_id: str = ""
    language: str = "bn"


@router.get("/whatsapp/automation/status")
async def whatsapp_automation_status():
    """Check WhatsApp automation status (OpenClaw + WhatsApp login)."""
    from app.services.whatsapp_automation import whatsapp_automation
    try:
        status = await asyncio.wait_for(whatsapp_automation.check_login_status(), timeout=5)
    except Exception:
        status = {"openclaw_available": False, "logged_in": False}
    return {
        "success": True,
        "openclaw_available": status.get("openclaw_available", False),
        "whatsapp_logged_in": status.get("logged_in", False),
        "phone": os.getenv("WHATSAPP_PHONE", ""),
    }


@router.post("/whatsapp/automation/send")
async def whatsapp_automation_send(req: WhatsAppSendRequest, user: dict = Depends(get_current_user)):
    """Send a WhatsApp message via OpenClaw browser automation."""
    from app.services.whatsapp_automation import whatsapp_automation
    from app.services.whatsapp_service import whatsapp_service

    if req.tender_id:
        try:
            tender = await load_tender_snapshot(req.tender_id)
            if tender:
                result = await whatsapp_automation.send_tender_alert(tender, phone=req.phone, lang=req.language)
                return {"success": result["success"], "method": result.get("method", "wa_link"), "result": result}
        except Exception as e:
            logger.warning(f"Tender lookup failed: {e}")

    if req.message:
        phone = req.phone or os.getenv("WHATSAPP_PHONE", "")
        result = await whatsapp_automation.send_message(phone, req.message)
        return {"success": result["success"], "method": result.get("method", "wa_link"), "result": result}

    return {"success": False, "error": "Provide message or tender_id"}


@router.post("/whatsapp/automation/send-batch")
async def whatsapp_automation_send_batch(req: Dict[str, Any], user: dict = Depends(get_current_user)):
    """Send batch tender alerts via OpenClaw."""
    from app.services.whatsapp_automation import whatsapp_automation
    tenders = req.get("tenders", [])
    phone = req.get("phone", "")
    lang = req.get("language", "bn")
    if not tenders:
        return {"success": False, "error": "No tenders provided"}
    result = await whatsapp_automation.send_batch_alerts(tenders, phone=phone, lang=lang)
    return {"success": True, "result": result}


# ── OpenClaw Browser Management Endpoints ─────────────────────────────

@router.get("/openclaw/status")
async def openclaw_status():
    """Check OpenClaw availability."""
    from app.services.openclaw_client import openclaw_client
    available = await openclaw_client.is_available()
    return {
        "success": True,
        "available": available,
        "base_url": os.getenv("OPENCLAW_BASE_URL", "http://localhost:18789"),
        "enabled": os.getenv("OPENCLAW_ENABLED", "true").lower() == "true",
    }


@router.post("/openclaw/browser/start")
async def openclaw_browser_start(headless: bool = False, user: dict = Depends(get_current_user)):
    """Start OpenClaw browser."""
    from app.services.openclaw_client import openclaw_client
    result = await openclaw_client.start(headless=headless)
    return {"success": result.get("success", False), "output": result.get("output", "")}


@router.post("/openclaw/browser/stop")
async def openclaw_browser_stop(user: dict = Depends(get_current_user)):
    """Stop OpenClaw browser."""
    from app.services.openclaw_client import openclaw_client
    result = await openclaw_client.stop()
    return {"success": result.get("success", False)}


@router.post("/openclaw/navigate")
async def openclaw_navigate(req: Dict[str, str], user: dict = Depends(get_current_user)):
    """Navigate to a URL."""
    from app.services.openclaw_client import openclaw_client
    url = req.get("url", "")
    if not url:
        return {"success": False, "error": "url required"}
    result = await openclaw_client.navigate(url)
    return {"success": result.get("success", False)}


@router.get("/openclaw/snapshot")
async def openclaw_snapshot():
    """Get page snapshot from OpenClaw."""
    from app.services.openclaw_client import openclaw_client
    result = await openclaw_client.snapshot()
    return {"success": result.get("success", False), "output": result.get("output", "")}
