"""Auth API routes — Multi-tenant authentication with password hashing"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import noload
from typing import Dict, Any

from pydantic import BaseModel

from app.core.security import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.services.refresh_token_service import (
    RefreshTokenError,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.schemas.auth import LoginRequest, Token
from app.schemas.response_models import (
    AuthTokenResponse,
    ChangePasswordResponse,
    LogoutResponse,
    MeResponse,
    RefreshTokenResponse,
)
from app.models.user import User, UserPlan
from app.db.base import get_async_session

router = APIRouter(prefix="/auth", tags=["auth"])

import time
from collections import defaultdict

# Simple in-memory rate limiter (per IP, per endpoint)
_rate_limit_store: dict = defaultdict(lambda: {"count": 0, "window_start": 0})


def check_rate_limit(client_ip: str, endpoint: str, max_requests: int = 5, window_seconds: int = 60):
    """Check if request is within rate limit."""
    key = f"{client_ip}:{endpoint}"
    now = time.time()
    entry = _rate_limit_store[key]
    if now - entry["window_start"] > window_seconds:
        entry["count"] = 0
        entry["window_start"] = now
    entry["count"] += 1
    if entry["count"] > max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds."
        )
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "owner@procureflow.local").strip().lower()
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "").strip()
OWNER_PASSWORD_ALIASES = [
    p.strip()
    for p in os.getenv("OWNER_PASSWORD_ALIASES", "").split(",")
    if p.strip()
]
OWNER_TENANT_ID = os.getenv("OWNER_TENANT_ID", "tenant-owner-zakaria-nasim").strip()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


async def ensure_owner_user(db: AsyncSession) -> User:
    stmt = select(User).options(noload("*")).where(User.email == OWNER_EMAIL)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    hashed = hash_password(OWNER_PASSWORD) if OWNER_PASSWORD else None

    if user:
        updated = False
        if hashed and not verify_password(OWNER_PASSWORD, user.hashed_password):
            user.hashed_password = hashed
            updated = True
        if user.plan != UserPlan.ENTERPRISE:
            user.plan = UserPlan.ENTERPRISE
            updated = True
        if not user.is_superuser:
            user.is_superuser = True
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True
        if not user.full_name:
            user.full_name = "Zakaria Nasim"
            updated = True
        if not getattr(user, "tenant_id", None):
            user.tenant_id = OWNER_TENANT_ID
            updated = True
        if getattr(user, "role", "viewer") != "owner":
            user.role = "owner"
            updated = True
        if updated:
            await db.commit()
            await db.refresh(user)
        return user

    if not hashed:
        raise HTTPException(
            status_code=500,
            detail="Owner account is not configured. Set OWNER_PASSWORD in backend/.env to bootstrap it.",
        )

    user = User(
        id="owner-zakaria-nasim",
        email=OWNER_EMAIL,
        hashed_password=hashed,
        full_name="Zakaria Nasim",
        tenant_id=OWNER_TENANT_ID,
        role="owner",
        plan=UserPlan.ENTERPRISE,
        is_active=True,
        is_superuser=True,
        gpt_quota_limit=500000,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """Login with email/password against database users only."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "/auth/login", max_requests=5, window_seconds=60)
    
    await ensure_owner_user(db)
    
    # Try database lookup first
    stmt = select(User).options(noload("*")).where(User.email == req.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        password_ok = verify_password(req.password, user.hashed_password)
        if not password_ok and user.email == OWNER_EMAIL:
            for alias in OWNER_PASSWORD_ALIASES:
                if req.password == alias:
                    password_ok = True
                    break
        if not password_ok:
            raise HTTPException(status_code=401, detail="Invalid password")
        
        role = getattr(user, "role", "viewer") or ("owner" if user.is_superuser else "viewer")
        tenant_id = getattr(user, "tenant_id", None)
        token = create_token(
            user.id,
            user.plan.value,
            tenant_id=tenant_id,
            role=role,
        )
        refresh_token = await issue_refresh_token(db, user.id, tenant_id)
        await db.commit()
        return {
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "plan": user.plan.value,
                "tenant_id": tenant_id,
                "role": role,
                "name": user.full_name or user.email.split("@")[0].title(),
            },
        }

    raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/register", response_model=AuthTokenResponse)
async def register(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_async_session)):
    """Register a new user with email/password."""
    import uuid

    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "/auth/register", max_requests=3, window_seconds=300)

    await ensure_owner_user(db)
    
    # Check if email already exists
    stmt = select(User).options(noload("*")).where(User.email == req.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed = hash_password(req.password)
    uid = req.email.split("@")[0]
    
    user = User(
        id=user_id,
        email=req.email,
        hashed_password=hashed,
        full_name=uid.title(),
        tenant_id=user_id,  # Use UUID directly — fits in VARCHAR(36/64)
        role="admin",
        plan=UserPlan.FREE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_token(user.id, UserPlan.FREE.value, tenant_id=user.tenant_id, role=user.role)
    refresh_token = await issue_refresh_token(db, user.id, user.tenant_id)
    await db.commit()

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "plan": UserPlan.FREE.value,
            "tenant_id": user.tenant_id,
            "role": user.role,
            "name": user.full_name,
        },
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    req: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Rotate a refresh token: new access + new refresh; reuse revokes the family (T-016)."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "/auth/refresh", max_requests=20, window_seconds=60)

    try:
        payload, new_refresh = await rotate_refresh_token(db, req.refresh_token)
    except RefreshTokenError:
        # Uniform 401 — no reason leakage to callers (reuse is audit-logged server-side)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    stmt = select(User).options(noload("*")).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or not found")

    role = getattr(user, "role", "viewer") or ("owner" if user.is_superuser else "viewer")
    tenant_id = getattr(user, "tenant_id", None)
    access_token = create_token(user.id, user.plan.value, tenant_id=tenant_id, role=role)
    await db.commit()
    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Revoke the presented refresh token's family (T-016). Idempotent."""
    await revoke_refresh_token(db, req.refresh_token, reason="logout")
    await db.commit()
    return {"success": True}


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current authenticated user info."""
    # Try to get full user from DB
    stmt = select(User).options(noload("*")).where(User.id == user["id"])
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if db_user:
        return {
            "success": True,
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.full_name,
                "plan": db_user.plan.value,
                "tenant_id": getattr(db_user, "tenant_id", None),
                "role": getattr(db_user, "role", "viewer"),
                "is_active": db_user.is_active,
                "gpt_quota_remaining": db_user.gpt_quota_limit - db_user.gpt_quota_used,
            },
        }
    
    # Fallback to JWT payload
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "plan": user["plan"],
            "tenant_id": user.get("tenant_id"),
            "role": user.get("role", "viewer"),
            "gpt_quota_remaining": user.get("gpt_quota", 50000),
        },
    }


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    data: Dict[str, str],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Change password for authenticated user."""
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Old and new password required")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    stmt = select(User).options(noload("*")).where(User.id == current_user["id"])
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(old_password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    db_user.hashed_password = hash_password(new_password)
    await db.commit()
    
    return {"success": True, "message": "Password changed successfully"}
