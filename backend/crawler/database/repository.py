from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import asyncpg

from .connection import get_db_pool
from ..framework.logger import get_logger

log = get_logger("crawler.repository")


class CrawlRepository:
    @staticmethod
    async def save_raw_data(table_name: str, source: str, data: dict) -> int:
        pool = await get_db_pool()
        data_hash = hashlib.md5(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO raw_crawl_data (table_name, source, data, data_hash, crawled_at)
                   VALUES ($1, $2, $3::jsonb, $4, $5)
                   RETURNING id""",
                table_name, source, json.dumps(data, default=str),
                data_hash, datetime.now(timezone.utc),
            )
            return row["id"] if row else 0

    @staticmethod
    async def find_duplicate(table_name: str, data_hash: str) -> bool:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM raw_crawl_data WHERE table_name=$1 AND data_hash=$2 LIMIT 1",
                table_name, data_hash,
            )
            return row is not None

    @staticmethod
    async def get_unprocessed_records(table_name: str, limit: int = 100) -> List[dict]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, data FROM raw_crawl_data
                   WHERE table_name=$1 AND processed=FALSE
                   ORDER BY crawled_at ASC LIMIT $2""",
                table_name, limit,
            )
            return [dict(r) for r in rows]

    @staticmethod
    async def mark_processed(record_id: int):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE raw_crawl_data SET processed=TRUE, processed_at=$1 WHERE id=$2",
                datetime.now(timezone.utc), record_id,
            )

    @staticmethod
    async def save_job(plugin: str, run_id: str, config: Optional[dict] = None) -> int:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO crawl_jobs (plugin, run_id, status, started_at, config)
                   VALUES ($1, $2, 'running', $3, $4::jsonb) RETURNING id""",
                plugin, run_id, datetime.now(timezone.utc),
                json.dumps(config) if config else None,
            )
            return row["id"] if row else 0

    @staticmethod
    async def finish_job(job_id: int, status: str, pages: int = 0, items: int = 0,
                         skipped: int = 0, failed: int = 0, error: Optional[str] = None):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE crawl_jobs SET status=$1, finished_at=$2, pages_done=$3,
                   items_done=$4, items_skipped=$5, items_failed=$6, error=$7 WHERE id=$8""",
                status, datetime.now(timezone.utc), pages, items, skipped, failed, error, job_id,
            )

    @staticmethod
    async def save_checkpoint(plugin: str, checkpoint_key: str, data: dict):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO crawl_checkpoints (plugin, checkpoint_key, data, updated_at)
                   VALUES ($1, $2, $3::jsonb, $4)
                   ON CONFLICT (plugin, checkpoint_key)
                   DO UPDATE SET data=$3::jsonb, updated_at=$4""",
                plugin, checkpoint_key, json.dumps(data, default=str),
                datetime.now(timezone.utc),
            )

    @staticmethod
    async def clear_checkpoint(plugin: str, checkpoint_key: str):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM crawl_checkpoints WHERE plugin=$1 AND checkpoint_key=$2",
                plugin, checkpoint_key,
            )

    @staticmethod
    async def get_checkpoint(plugin: str, checkpoint_key: str) -> Optional[dict]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM crawl_checkpoints WHERE plugin=$1 AND checkpoint_key=$2",
                plugin, checkpoint_key,
            )
            if not row:
                return None
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            return data if isinstance(data, dict) else None

    @staticmethod
    async def save_document(tender_id: str, doc_type: str, filename: str,
                            file_path: str, file_size: int, source_url: Optional[str] = None,
                            file_hash: Optional[str] = None, minio_path: Optional[str] = None,
                            metadata: Optional[dict] = None):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO crawl_documents (tender_id, doc_type, filename, file_path,
                   file_size, source_url, file_hash, minio_path, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)""",
                tender_id, doc_type, filename, file_path, file_size,
                source_url, file_hash, minio_path,
                json.dumps(metadata) if metadata else None,
            )

    @staticmethod
    async def log_error(run_id: Optional[str], plugin: str, error_type: str,
                         error_message: str, url: Optional[str] = None,
                         traceback: Optional[str] = None):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO crawl_errors (run_id, plugin, error_type, error_message, url, traceback)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                run_id, plugin, error_type, error_message, url, traceback,
            )

    @staticmethod
    async def save_tender_record(tender_id: str, record: dict,
                                  table: str = "raw_tenders") -> int:
        """Save a tender record and detect changes."""
        pool = await get_db_pool()
        data_hash = hashlib.md5(
            json.dumps(record, sort_keys=True, default=str).encode()
        ).hexdigest()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO raw_crawl_data (table_name, source, data, data_hash, crawled_at)
                   VALUES ($1, 'eprocure_tender', $2::jsonb, $3, $4)
                   RETURNING id""",
                table, json.dumps(record, default=str),
                data_hash, datetime.now(timezone.utc),
            )
            return row["id"] if row else 0

    @staticmethod
    async def get_last_tender_record(tender_id: str,
                                      table: str = "raw_tenders") -> Optional[dict]:
        """Get the most recent saved record for a tender_id."""
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT data, data_hash FROM raw_crawl_data
                   WHERE table_name=$1 AND data->>'tender_id'=$2
                   ORDER BY crawled_at DESC LIMIT 1""",
                table, tender_id,
            )
            if not row:
                return None
            result = dict(row)
            if isinstance(result.get("data"), str):
                result["data"] = json.loads(result["data"])
            return result

    @staticmethod
    async def detect_changes(tender_id: str, new_data: dict,
                              table: str = "raw_tenders") -> Optional[dict]:
        """Compare new_data with last saved version. Returns dict of changed fields or None."""
        last = await CrawlRepository.get_last_tender_record(tender_id, table)
        if not last:
            return None
        previous = last.get("data", {})
        if isinstance(previous, str):
            previous = json.loads(previous)
        if not isinstance(previous, dict):
            return None
        changes = {}
        for key in set(list(new_data.keys()) + list(previous.keys())):
            old_val = str(previous.get(key, ""))
            new_val = str(new_data.get(key, ""))
            if old_val != new_val:
                changes[key] = {"from": old_val, "to": new_val}
        return changes if changes else None

    @staticmethod
    async def log_change(table: str, record_id: str, change_type: str,
                          previous: Optional[dict] = None,
                          new_data: Optional[dict] = None,
                          fields: Optional[dict] = None):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO crawl_change_log
                   (table_name, record_id, change_type, previous_data, new_data, changed_fields)
                   VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb)""",
                table, record_id, change_type,
                json.dumps(previous) if previous else None,
                json.dumps(new_data) if new_data else None,
                json.dumps(fields) if fields else None,
            )
