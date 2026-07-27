"""
Legacy-compatibility shim for the database layer.

All 40+ consumers that import from ``app.db.base`` continue to work unchanged.
Under the hood, these functions delegate to ``app.db.database`` (PostgreSQL-only),
and ``init_db`` creates tables from BOTH the main ORM models (``app.db.models``)
and the intelligence models (``app.models``).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from pathlib import Path


class Base(DeclarativeBase):
    """
    Legacy ORM base — intentionally empty. All active models inherit from
    ``app.models.base.Base`` (which shares ``MetaData`` with this class to
    keep Alembic migrations unified). Do NOT map new models here.

    Why two bases?
    - ``app.db.models`` (legacy) uses the old ``declarative_base()`` pattern.
    - ``app.models.*`` (new) use ``app.models.base.Base`` with shared metadata.
    Both write to the same PG schema, but model classes are NOT interchangeable
    across the two hierarchies. See ``app.models.base`` for the canonical base.
    """
    pass


# ---------------------------------------------------------------------------
# Lazy-forward to the canonical database module
# ---------------------------------------------------------------------------
def _canonical():
    from app.db import database
    return database


def get_database_url() -> str:
    """Return the resolved async database URL (PostgreSQL)."""
    return _canonical().DATABASE_URL


engine = None
_session_factory = None


def get_engine():
    """Return the singleton async engine from the canonical module."""
    global engine
    if engine is None:
        engine = _canonical().get_engine()
    return engine


def get_session_factory():
    """Return an async session factory bound to the canonical engine."""
    global _session_factory
    if _session_factory is None:
        eng = get_engine()
        _session_factory = async_sessionmaker(
            eng,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db():
    """
    Create all tables from BOTH model sets:
      - app.db.models.Base  (33+ tables: Tenders, Awards, APP, Users, …)
      - app.models.Base      (intelligence tables: ContractorDNA, …)

    NOTE: app.models.Base is created FIRST because several of its tables
    (users, tenders, app_records, contracts, knowledge_entries, …) have
    the canonical schema.  app.db.models.Base is created second so that
    its overlapping tables are skipped (already exist with the right cols).

    ⚠️  This function calls `Base.metadata.create_all()` which BYPASSES
    Alembic.  In production, this will RAISE an error to prevent schema
    drift.  Run `alembic upgrade head` instead.  init_db() is only safe
    in development/test environments (ENVIRONMENT=development|dev|local|test).
    """
    import logging
    from app.core.config import settings as core_settings

    logger = logging.getLogger(__name__)
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    _DEV_ENVIRONMENTS = {"development", "dev", "local", "test"}
    if environment not in _DEV_ENVIRONMENTS:
        raise RuntimeError(
            "init_db() is DISABLED in production environments. "
            "Use `alembic upgrade head` for schema management (W-001). "
            f"Current ENVIRONMENT={environment!r}. "
            "To override this restriction, temporarily set "
            "ENVIRONMENT=development ( NEVER commit the change )."
        )
    logger.warning(
        "init_db() called in development mode: Base.metadata.create_all() "
        "BYPASSES Alembic. Run `alembic upgrade head` to keep migrations in sync."
    )
    # 1. Intelligence models FIRST (canonical schema wins for conflicts)
    from app.models import Base as IntelBase
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(IntelBase.metadata.create_all)

    # 2. Main ORM models SECOND (conflicts skipped via checkfirst=True)
    from app.db import database
    await database.init_db()


async def close_db():
    """Dispose the engine via the canonical module."""
    global engine, _session_factory
    engine = None
    _session_factory = None
    await _canonical().close_db()


def _request_rls_context(request: Optional[Request]) -> tuple[str, str]:
    if request is None:
        return "__no_tenant__", "false"
    user = getattr(request.state, "user", None) or {}
    tenant_id = str(
        user.get("tenant_id")
        or request.headers.get("x-tenant-id")
        or "__no_tenant__"
    )
    role = str(user.get("role") or "").lower()
    scopes = set(user.get("scopes") or [])
    is_superuser = "true" if role in {"owner", "admin"} or "*" in scopes else "false"
    return tenant_id[:120], is_superuser


async def _apply_rls_context(session: AsyncSession, request: Optional[Request]) -> None:
    """Apply tenant context via the central mechanism (SEC-02/T-015).

    The request middleware sets the contextvar for the whole request; when it
    is absent (direct dependency invocation, tests), fall back to deriving it
    from the request. Session-level GUCs — previously these were transaction-
    scoped and silently vanished after any mid-request commit.
    """
    database = _canonical()
    if database.get_tenant_context() is not None:
        await database.apply_tenant_context(session)
        return
    tenant_id, is_superuser = _request_rls_context(request)
    token = database.set_tenant_context(tenant_id, is_superuser=is_superuser == "true")
    try:
        await database.apply_tenant_context(session)
    finally:
        database.reset_tenant_context(token)


async def get_async_session(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session."""
    sf = get_session_factory()
    async with sf() as session:
        try:
            await _apply_rls_context(session, request)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """Proper FastAPI yield dependency for async DB sessions."""
    sf = get_session_factory()
    async with sf() as session:
        try:
            await _apply_rls_context(session, request)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
