from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..framework.config import settings
from ..framework.logger import get_logger

log = get_logger("crawler.database")

_pool: Optional[asyncpg.Pool] = None
_async_engine: Optional[AsyncEngine] = None
_async_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _get_db_url() -> str:
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url.replace("postgresql://", "postgresql+asyncpg://")
    pg_url = settings.storage_postgres_url
    if pg_url:
        return pg_url.replace("postgresql://", "postgresql+asyncpg://")
    return "postgresql+asyncpg://postgres:procurementflow@localhost:5433/procureflow_bd"


async def create_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = _get_db_url().replace("+asyncpg", "")
        _pool = await asyncpg.create_pool(
            url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        log.info("database_pool_created")
    return _pool


async def get_db_pool() -> asyncpg.Pool:
    if _pool is None:
        return await create_pool()
    return _pool


async def get_async_engine() -> AsyncEngine:
    global _async_engine
    if _async_engine is None:
        url = _get_db_url()
        _async_engine = create_async_engine(url, pool_size=5, max_overflow=5, echo=False)
    return _async_engine


async def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _async_sessionmaker
    if _async_sessionmaker is None:
        engine = await get_async_engine()
        _async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    return _async_sessionmaker


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("database_pool_closed")


async def close_engine():
    global _async_engine
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        log.info("database_engine_closed")
