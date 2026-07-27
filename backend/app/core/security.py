"""
Procurement Flow Specialist BD — Security & Auth Utilities
JWT creation/validation, password hashing, user dependency injection.
"""

from __future__ import annotations

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer(auto_error=False)

# ── Password Hashing (bcrypt) ────────────────────────────────────────────
import bcrypt

def hash_password(password: str) -> str:
    """Hash password with bcrypt (adaptive, slow, secure)."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, AttributeError):
        return False


# ── Legacy SHA-256 support for migration ──────────────────────────────────

def verify_password_legacy(password: str, hashed: str) -> bool:
    """Verify legacy SHA-256 hash (for migration only)."""
    try:
        salt, pwd_hash = hashed.split("$")
        return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash
    except (ValueError, AttributeError):
        return False


def verify_password_with_fallback(password: str, hashed: str) -> bool:
    """Verify password, trying bcrypt first, then legacy SHA-256."""
    if not hashed:
        return False
    if hashed.startswith('$2'):
        return verify_password(password, hashed)
    return verify_password_legacy(password, hashed)


# ── JWT Tokens ────────────────────────────────────────────────────────────

ROLE_SCOPES = {
    "owner": ["*"],
    "admin": ["*"],
    "manager": ["read", "write", "approve"],
    "estimator": ["read", "write"],
    "viewer": ["read"],
}


def create_token(
    user_id: str,
    plan: str = "free",
    extra: Optional[dict] = None,
    tenant_id: Optional[str] = None,
    role: str = "viewer",
    scopes: Optional[list[str]] = None,
    expires_in_hours: Optional[int] = None,
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    expire_hours = expires_in_hours or settings.JWT_EXPIRE_HOURS
    expire = now + timedelta(hours=expire_hours)
    role = (role or "viewer").lower()
    payload = {
        "sub": user_id,
        "exp": expire,
        "plan": plan,
        "iat": now,
        "tenant_id": tenant_id,
        "role": role,
        "scopes": scopes if scopes is not None else ROLE_SCOPES.get(role, ["read"]),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    tenant_id: Optional[str] = None,
) -> str:
    """Create a long-lived refresh token (30 days)."""
    import uuid

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
        "tenant_id": tenant_id,
        # unique per issuance — required for server-side rotation records (T-016)
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALGORITHM)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex of the raw refresh token — only the hash is persisted (T-016)."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_refresh_token(token: str) -> dict:
    """Decode and validate refresh token."""
    secrets_to_try = [settings.JWT_REFRESH_SECRET, *settings.JWT_PREVIOUS_SECRETS]
    last_error = None
    for secret in secrets_to_try:
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                raise jwt.InvalidTokenError("Not a refresh token")
            return payload
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as exc:
            last_error = exc
    raise last_error or jwt.InvalidTokenError("Invalid refresh token")


def decode_token(token: str) -> dict:
    """Decode and validate JWT token against current and rotation secrets."""
    secrets_to_try = [settings.JWT_SECRET, *settings.JWT_PREVIOUS_SECRETS]
    last_error: jwt.InvalidTokenError | None = None
    for secret in secrets_to_try:
        try:
            return jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as exc:
            last_error = exc
    raise last_error or jwt.InvalidTokenError("Invalid token")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token (raises 401 if invalid)."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = decode_token(credentials.credentials)
        return {
            "id": payload["sub"],
            "plan": payload.get("plan", "free"),
            "tenant_id": payload.get("tenant_id"),
            "role": payload.get("role", "viewer"),
            "scopes": payload.get("scopes", ["read"]),
            "gpt_quota": 50000,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Get current user or return guest (no auth required)."""
    if credentials is None:
        return {"id": "guest", "plan": "demo", "gpt_quota": 10}
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return {"id": "guest", "plan": "demo", "gpt_quota": 10}


def require_scope(required: str):
    async def _dependency(user: dict = Depends(get_current_user)) -> dict:
        scopes = set(user.get("scopes") or [])
        if "*" not in scopes and required not in scopes:
            raise HTTPException(status_code=403, detail=f"Missing required scope: {required}")
        return user
    return _dependency


def require_role(*roles: str):
    allowed = {role.lower() for role in roles}

    async def _dependency(user: dict = Depends(get_current_user)) -> dict:
        role = str(user.get("role") or "viewer").lower()
        scopes = set(user.get("scopes") or [])
        if "*" not in scopes and role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return _dependency
