"""
Database connection and session management.
PostgreSQL-only backend.
"""
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, Engine, text

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# DB credentials live in backend/.env; load that FIRST (it holds POSTGRES_PASSWORD /
# DATABASE_URL). Fall back to the repo-root .env for any vars it doesn't define.
# Without this the URLs resolve with an EMPTY password at import time (before the
# app's own load_dotenv runs), which auth-fails on the async engine.
load_dotenv(Path(_PROJECT_ROOT) / ".env")
load_dotenv(Path(_PROJECT_ROOT).parent / ".env")


def _build_postgres_urls() -> tuple[str, str]:
    user = os.getenv("POSTGRES_USER", os.getenv("PGUSER", "postgres"))
    password = os.getenv("POSTGRES_PASSWORD", os.getenv("PGPASSWORD", ""))
    host = os.getenv("POSTGRES_HOST", os.getenv("PGHOST", "localhost"))
    port = os.getenv("POSTGRES_PORT", os.getenv("PGPORT", "5433"))
    database = os.getenv("POSTGRES_DB", os.getenv("PGDATABASE", "procureflow_bd"))
    safe_password = quote_plus(password)
    # asyncpg resolves "localhost" to IPv6 (::1) first; if PostgreSQL only listens
    # on IPv4 the connection is refused (WinError 1225) while psycopg2 (sync) still
    # works. Pin the async driver to IPv4 so both drivers reach the same server.
    async_host = "127.0.0.1" if host in ("localhost", "::1") else host
    async_url = f"postgresql+asyncpg://{user}:{safe_password}@{async_host}:{port}/{database}"
    sync_url = f"postgresql+psycopg2://{user}:{safe_password}@{host}:{port}/{database}"
    return async_url, sync_url


def _resolve_database_urls() -> tuple[str, str]:
    explicit_async = os.getenv("DATABASE_URL")
    explicit_sync = os.getenv("SYNC_DATABASE_URL")
    
    if explicit_async:
        # Normalize async URL: must use postgresql+asyncpg:// driver
        if explicit_async.startswith("postgresql://") and not explicit_async.startswith("postgresql+"):
            explicit_async = explicit_async.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif explicit_async.startswith("postgresql+psycopg2://"):
            explicit_async = explicit_async.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        elif not explicit_async.startswith("postgresql+"):
            raise ValueError(
                f"DATABASE_URL must be a PostgreSQL URL (got: {explicit_async[:30]}...). "
                f"Supported: postgresql://..., postgresql+asyncpg://..."
            )
    
    if explicit_sync:
        # Normalize sync URL: must use postgresql+psycopg2:// driver
        if explicit_sync.startswith("postgresql://") and not explicit_sync.startswith("postgresql+"):
            explicit_sync = explicit_sync.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif explicit_sync.startswith("postgresql+asyncpg://"):
            explicit_sync = explicit_sync.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        elif not explicit_sync.startswith("postgresql+"):
            raise ValueError(
                f"SYNC_DATABASE_URL must be a PostgreSQL URL (got: {explicit_sync[:30]}...). "
                f"Supported: postgresql://..., postgresql+psycopg2://..."
            )
    
    if explicit_async and explicit_sync:
        return explicit_async, explicit_sync
    if explicit_async and not explicit_sync:
        return explicit_async, explicit_async.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if explicit_sync and not explicit_async:
        return explicit_sync.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1), explicit_sync
    return _build_postgres_urls()


DATABASE_URL, SYNC_DATABASE_URL = _resolve_database_urls()

# ── PgBouncer routing (DB-03/T-011) ─────────────────────────────────────
# The async engine (API + Celery workers) routes through PgBouncer when
# PGBOUNCER_URL is set. Alembic and get_sync_engine() always use
# SYNC_DATABASE_URL (direct :5433) — migrations and DDL must bypass the
# pooler (transaction-mode PgBouncer cannot safely carry DDL/advisory locks).
_PGBOUNCER_URL = os.getenv("PGBOUNCER_URL", "").strip()


def _resolve_async_engine_url() -> str:
    if not _PGBOUNCER_URL:
        return DATABASE_URL
    url = _PGBOUNCER_URL
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


def using_pgbouncer() -> bool:
    return bool(_PGBOUNCER_URL)


def _async_connect_args() -> dict:
    if not _PGBOUNCER_URL:
        return {}
    # Transaction-mode pooling reassigns the backend connection between
    # statements, so asyncpg's server-side prepared-statement cache (keyed to
    # a specific backend connection) must be disabled (ADR-010 risk).
    return {"statement_cache_size": 0}


# ── Tenant context (SEC-02/T-015, ADR-007/020) ─────────────────────────
# Single mechanism for every session-acquisition path (API middleware,
# Celery tasks, agents, scripts): callers set the contextvar; every central
# session helper applies it as the app.tenant_id / app.is_superuser GUCs
# that migration 011's RLS policies read. Session-level (not transaction-
# level) so the context survives mid-request commits, and ALWAYS re-applied
# on acquisition so a pooled connection can never leak the previous
# checkout's tenant.
NO_TENANT = "__no_tenant__"

_TENANT_CONTEXT: ContextVar[Optional[tuple]] = ContextVar("procureflow_tenant_context", default=None)

# Module attribute (not read per-call from env) so tests can patch it — when
# true, acquiring a session without tenant context raises instead of
# defaulting to NO_TENANT.
_STRICT_TENANT_CONTEXT = os.getenv("RLS_STRICT_CONTEXT", "false").strip().lower() == "true"


class MissingTenantContextError(RuntimeError):
    """A DB session was acquired without tenant context while RLS_STRICT_CONTEXT is on."""


def set_tenant_context(tenant_id: Optional[str], *, is_superuser: bool = False):
    """Set the calling context's tenant; returns a contextvars Token for reset."""
    tid = str(tenant_id or NO_TENANT)[:120]
    return _TENANT_CONTEXT.set((tid, bool(is_superuser)))


def reset_tenant_context(token) -> None:
    _TENANT_CONTEXT.reset(token)


def get_tenant_context() -> Optional[tuple]:
    """Return (tenant_id, is_superuser) or None if no context was set."""
    return _TENANT_CONTEXT.get()


@contextmanager
def tenant_context(tenant_id: Optional[str], *, is_superuser: bool = False):
    """Scope tenant context around a block — the wrapper for Celery tasks/scripts."""
    token = set_tenant_context(tenant_id, is_superuser=is_superuser)
    try:
        yield
    finally:
        reset_tenant_context(token)


def _resolve_tenant_context() -> tuple:
    ctx = _TENANT_CONTEXT.get()
    if ctx is None:
        if _STRICT_TENANT_CONTEXT:
            raise MissingTenantContextError(
                "DB session acquired without tenant context — wrap the caller in "
                "tenant_context(...) or set_tenant_context(...) (ADR-020)."
            )
        ctx = (NO_TENANT, False)
    return ctx


async def apply_tenant_context(session: AsyncSession) -> None:
    """Apply the current tenant context to a session (session-level GUCs)."""
    tenant_id, is_superuser = _resolve_tenant_context()
    await session.execute(
        text(
            "SELECT set_config('app.tenant_id', :tenant_id, false), "
            "set_config('app.is_superuser', :is_superuser, false)"
        ),
        {"tenant_id": tenant_id, "is_superuser": "true" if is_superuser else "false"},
    )


def apply_tenant_context_sync(session) -> None:
    """Sync-session variant of apply_tenant_context (session_scope, scripts)."""
    tenant_id, is_superuser = _resolve_tenant_context()
    session.execute(
        text(
            "SELECT set_config('app.tenant_id', :tenant_id, false), "
            "set_config('app.is_superuser', :is_superuser, false)"
        ),
        {"tenant_id": tenant_id, "is_superuser": "true" if is_superuser else "false"},
    )


_engine: AsyncEngine | None = None
_sync_engine: Engine | None = None
_session_factory = None
_sync_session_factory = None

# ── Read Replica support (P1-8) ───────────────────────────────────────
_READ_REPLICA_URL = os.getenv("READ_REPLICA_URL", "")
_read_replica_engine: AsyncEngine | None = None
_read_replica_session_factory = None


def get_read_replica_url() -> str | None:
    """Return the read-replica async URL, or None if not configured."""
    if not _READ_REPLICA_URL:
        return None
    url = _READ_REPLICA_URL
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif not url.startswith("postgresql+"):
        raise ValueError(f"READ_REPLICA_URL must be a PostgreSQL URL (got: {url[:30]}...)")
    return url


def get_read_replica_engine() -> AsyncEngine | None:
    """Lazy-init the read-replica async engine."""
    global _read_replica_engine
    if _read_replica_engine is None:
        url = get_read_replica_url()
        if url:
            _read_replica_engine = create_async_engine(
                url,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
                future=True,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            logger.info("Read-replica engine created: %s", url.split("@")[-1])
    return _read_replica_engine


def get_read_replica_session() -> AsyncSession | None:
    """Return a read-only async session bound to the replica, or None."""
    global _read_replica_session_factory
    engine = get_read_replica_engine()
    if not engine:
        return None
    if _read_replica_session_factory is None:
        _read_replica_session_factory = sessionmaker(
            engine,
            class_=TenantAwareAsyncSession,
            expire_on_commit=False,
        )
    return _read_replica_session_factory()


@asynccontextmanager
async def get_read_session():
    """
    Yield a read-only session (read-replica if configured, else primary).

    Usage:
        async with get_read_session() as session:
            rows = await session.execute(select(...))
    """
    replica = get_read_replica_session()
    if replica:
        try:
            yield replica
        finally:
            await replica.close()
    else:
        async with get_async_session() as session:
            yield session


# ── Primary database helpers ────────────────────────────────────────────


def get_database_backend() -> str:
    if DATABASE_URL.startswith("postgresql"):
        return "postgresql"
    return "unknown"


def get_database_summary() -> dict:
    return {
        "backend": "postgresql",
        "host": os.getenv("POSTGRES_HOST", os.getenv("PGHOST", "localhost")),
        "port": os.getenv("POSTGRES_PORT", os.getenv("PGPORT", "5433")),
        "database": os.getenv("POSTGRES_DB", os.getenv("PGDATABASE", "procureflow_bd")),
        "user": os.getenv("POSTGRES_USER", os.getenv("PGUSER", "postgres")),
    }


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # W-016: When routing through PgBouncer, reduce app-side pool since
        # PgBouncer manages the aggregate connection pool. When direct, use larger pool.
        pool_sz = 5 if using_pgbouncer() else 20
        overflow = 10 if using_pgbouncer() else 40

        _engine = create_async_engine(
            _resolve_async_engine_url(),
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            future=True,
            pool_size=pool_sz,
            max_overflow=overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args=_async_connect_args(),
        )
        logger.info(
            "Database engine created: %s (via_pgbouncer=%s)",
            get_database_summary(), using_pgbouncer(),
        )
    return _engine


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        from sqlalchemy import create_engine as sync_create
        # Sync engine always connects directly (not through PgBouncer) for DDL/migrations
        _sync_engine = sync_create(
            SYNC_DATABASE_URL,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            future=True,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _sync_engine


def get_sync_session():
    """Return a reusable synchronous SQLAlchemy Session with tenant context."""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            get_sync_engine(),
            expire_on_commit=False,
        )
    session = _sync_session_factory()
    apply_tenant_context_sync(session)
    return session


@contextmanager
def session_scope():
    """Provide a transactional scope around a synchronous session."""
    session = get_sync_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db():
    """Create tables from app.db.models Base metadata.

    ⚠️ WARNING: This calls `Base.metadata.create_all()` which BYPASSES
    Alembic.  In production, run `alembic upgrade head` first and use
    this only as a fallback.  Schema drift from runtime `create_all` is
    invisible to `alembic revision --autogenerate`.
    """
    logger.warning(
        "database.init_db() called: Base.metadata.create_all() BYPASSES Alembic. "
        "Run `alembic upgrade head` for tracked schema management."
    )
    from .models import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def close_db():
    global _engine, _sync_engine, _session_factory, _sync_session_factory
    global _read_replica_engine, _read_replica_session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Async database engine disposed")
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
        logger.info("Sync database engine disposed")
    if _read_replica_engine:
        await _read_replica_engine.dispose()
        _read_replica_engine = None
        logger.info("Read-replica engine disposed")
    _session_factory = None
    _sync_session_factory = None
    _read_replica_session_factory = None


class TenantAwareAsyncSession(AsyncSession):
    """AsyncSession that applies tenant context on first execute (ADR-020).

    Every session acquisition path (API, worker, agent, script) automatically
    sets ``app.tenant_id`` / ``app.is_superuser`` GUCs before the first query,
    so RLS policies are satisfied even when callers use raw ``get_session()``
    instead of the wrapped ``get_async_session()`` context manager.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tenant_applied = False

    async def execute(self, statement, params=None, **kwargs):
        if not self._tenant_applied:
            self._tenant_applied = True
            await apply_tenant_context(self)
        return await super().execute(statement, params=params, **kwargs)


def get_session() -> AsyncSession:
    """Get a new async session with tenant context auto-applied."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            get_engine(),
            class_=TenantAwareAsyncSession,
            expire_on_commit=False,
        )
    return _session_factory()


@asynccontextmanager
async def get_async_session():
    _resolve_tenant_context()
    session = get_session()
    try:
        yield session
    finally:
        await session.close()


async def get_read_db():
    """FastAPI dependency: yield a read-only session (replica → primary fallback).

    T-034 (ENT-07): all read-heavy dashboard/analytics endpoints should declare
    ``db: AsyncSession = Depends(get_read_db)`` so queries route to the read
    replica when READ_REPLICA_URL is set, falling back to the primary when not.
    The session still carries full tenant context (TenantAwareAsyncSession).
    """
    async with get_read_session() as session:
        yield session


async def check_replica_lag() -> dict:
    """Query the primary for replication lag to each connected standby.

    Returns a dict with keys:
      - ``has_replica``: True when READ_REPLICA_URL is configured
      - ``replication_slots``: list of {slot_name, lag_bytes, lag_seconds}
      - ``max_lag_seconds``: worst lag across all standbys, or None if no standbys
    """
    result = {
        "has_replica": bool(_READ_REPLICA_URL),
        "replication_slots": [],
        "max_lag_seconds": None,
    }
    try:
        async with get_engine().connect() as conn:
            rows = await conn.execute(
                text(
                    "SELECT application_name, "
                    "EXTRACT(EPOCH FROM (now() - sent_lsn::text::pg_lsn::timestamp)) AS lag_seconds, "
                    "pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes "
                    "FROM pg_stat_replication"
                )
            )
            slots = [
                {
                    "slot_name": r[0],
                    "lag_seconds": float(r[1]) if r[1] is not None else None,
                    "lag_bytes": int(r[2]) if r[2] is not None else None,
                }
                for r in rows.fetchall()
            ]
            result["replication_slots"] = slots
            lag_values = [s["lag_seconds"] for s in slots if s["lag_seconds"] is not None]
            result["max_lag_seconds"] = max(lag_values) if lag_values else None
    except Exception as exc:
        logger.debug("check_replica_lag: pg_stat_replication unavailable: %s", exc)
    return result


async def check_database_health() -> dict:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        replica_status = {
            "configured": bool(_READ_REPLICA_URL),
            "active": bool(get_read_replica_url()),
        }
        return {
            "status": "healthy",
            "backend": "postgresql",
            "via_pgbouncer": using_pgbouncer(),
            "read_replica": replica_status,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "backend": "postgresql",
            "via_pgbouncer": using_pgbouncer(),
        }


@event.listens_for(Engine, "connect")
def _set_pg_connection_options(dbapi_connection, connection_record):
    """Set PostgreSQL session options on new connections."""
    if hasattr(dbapi_connection, "cursor"):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET statement_timeout = '300s'")
            cursor.close()
        except Exception as e:
            logger.warning("Failed to set PG connection options: %s", e)
