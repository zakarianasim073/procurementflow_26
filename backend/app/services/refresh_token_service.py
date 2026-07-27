"""Refresh-token issuance, rotation, reuse detection, revocation (T-016/SEC-03).

Design (ADR-007 'no token rotation' consequence closed):
- Every issued refresh token is persisted as a SHA-256 hash with a family_id.
- Rotation marks the old record rotated and issues a new token in the same family.
- Presenting an already-rotated token is REUSE: the whole family is revoked and
  the event is audit-logged (a stolen-then-rotated token kills the session tree).
- Logout revokes the presented token's family.
- settings.REFRESH_TOKEN_ROTATION=False restores legacy stateless behavior
  (rollback path) — tokens validate by JWT signature only.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_refresh_token, decode_refresh_token, hash_refresh_token
from app.models.user import RefreshToken

logger = logging.getLogger(__name__)


class RefreshTokenError(Exception):
    """Invalid/revoked/reused refresh token — maps to HTTP 401 at the router."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def issue_refresh_token(
    db: AsyncSession,
    user_id: str,
    tenant_id: Optional[str] = None,
    *,
    family_id: Optional[str] = None,
) -> str:
    """Create a refresh token and persist its hash. Commits are the caller's job."""
    token = create_refresh_token(user_id, tenant_id=tenant_id)
    if not settings.REFRESH_TOKEN_ROTATION:
        return token

    payload = decode_refresh_token(token)
    db.add(RefreshToken(
        id=payload["jti"],
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=hash_refresh_token(token),
        family_id=family_id or payload["jti"],
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    ))
    return token


async def _revoke_family(db: AsyncSession, family_id: str, reason: str) -> int:
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_utcnow(), revoke_reason=reason)
    )
    return result.rowcount or 0


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> Tuple[dict, str]:
    """Validate + rotate. Returns (jwt payload, new refresh token).

    Raises RefreshTokenError on invalid/expired/revoked tokens; on REUSE of an
    already-rotated token the whole family is revoked first (and committed —
    revocation must survive the request's 401).
    """
    try:
        payload = decode_refresh_token(raw_token)
    except Exception:
        raise RefreshTokenError("invalid")

    if not settings.REFRESH_TOKEN_ROTATION:
        # Legacy stateless mode: signature-valid is sufficient
        return payload, create_refresh_token(payload.get("sub"), tenant_id=payload.get("tenant_id"))

    record = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )).scalar_one_or_none()

    if record is None:
        # Signature-valid but unknown to the store (pre-T-016 token, or a
        # record deleted server-side) — fail closed.
        raise RefreshTokenError("unknown")

    if record.revoked_at is not None:
        raise RefreshTokenError("revoked")

    if record.rotated_at is not None:
        # REUSE: this token was already exchanged once — treat the family as stolen
        revoked = await _revoke_family(db, record.family_id, "reuse-detected")
        await _audit_reuse(db, record, revoked)
        await db.commit()
        logger.warning(
            "Refresh-token reuse detected: user=%s family=%s (%d tokens revoked)",
            record.user_id, record.family_id, revoked,
        )
        raise RefreshTokenError("reuse-detected")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _utcnow():
        raise RefreshTokenError("expired")

    new_token = await issue_refresh_token(
        db, record.user_id, record.tenant_id, family_id=record.family_id
    )
    record.rotated_at = _utcnow()
    record.replaced_by = decode_refresh_token(new_token)["jti"]
    return payload, new_token


async def revoke_refresh_token(db: AsyncSession, raw_token: str, reason: str = "logout") -> bool:
    """Revoke the presented token's family (logout). Idempotent; commits are the caller's job."""
    if not settings.REFRESH_TOKEN_ROTATION:
        return False
    record = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )).scalar_one_or_none()
    if record is None:
        return False
    await _revoke_family(db, record.family_id, reason)
    return True


async def _audit_reuse(db: AsyncSession, record: RefreshToken, revoked_count: int) -> None:
    from app.services.audit_service import log_audit_event

    await log_audit_event(
        db,
        tenant_id=record.tenant_id,
        actor_id=record.user_id,
        actor_type="auth",
        action="refresh_token_reuse_detected",
        resource_type="refresh_token_family",
        resource_id=record.family_id,
        status="revoked",
        metadata={"tokens_revoked": revoked_count, "token_id": record.id},
    )
