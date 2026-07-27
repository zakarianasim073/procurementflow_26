from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from .config import settings, StorageBackend
from .logger import get_logger

log = get_logger("crawler.storage")

OUTPUT_DIR = Path("output/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_locks: Dict[str, Lock] = {}


def _get_lock(table: str) -> Lock:
    if table not in _locks:
        _locks[table] = Lock()
    return _locks[table]


class StorageManager:
    def __init__(self):
        self.backend = settings.storage_backend
        self._json_dir = settings.output_dir
        self._json_dir.mkdir(parents=True, exist_ok=True)
        self._pg_available = False
        self._minio_available = False
        self._pg_pool = None

    async def initialize(self):
        if self.backend in (StorageBackend.POSTGRESQL, StorageBackend.BOTH):
            try:
                from .database import get_db_pool
                self._pg_pool = await get_db_pool()
                self._pg_available = True
                log.info("postgresql_storage_available")
            except Exception as e:
                log.warning("postgresql_unavailable, falling back to JSONL", error=e)
                self._pg_available = False

        if self.backend in (StorageBackend.MINIO, StorageBackend.BOTH):
            if settings.storage_minio_endpoint:
                try:
                    from minio import Minio
                    client = Minio(
                        settings.storage_minio_endpoint,
                        access_key=settings.storage_minio_access_key,
                        secret_key=settings.storage_minio_secret_key,
                        secure=False,
                    )
                    if not client.bucket_exists(settings.storage_minio_bucket):
                        client.make_bucket(settings.storage_minio_bucket)
                    self._minio_available = True
                    log.info("minio_storage_available")
                except Exception as e:
                    log.warning("minio_unavailable", error=e)
                    self._minio_available = False
        log.info("storage_initialized", backend=self.backend.value)

    async def save(self, table: str, source: str, data: dict) -> bool:
        record = {
            "source": source,
            "raw_data": data,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }

        saved = True

        if self.backend in (StorageBackend.POSTGRESQL, StorageBackend.BOTH) and self._pg_available:
            try:
                await self._save_to_pg(table, source, data)
            except Exception as e:
                log.warning("pg_save_failed, falling back", table=table, error=e)
                saved = False

        if self.backend in (StorageBackend.JSONL, StorageBackend.BOTH) or not saved:
            save_raw_record(table, source, data)

        return True

    async def save_document(self, tender_id: str, doc_type: str, file_path: Path) -> bool:
        doc_path = settings.download_temp_path / tender_id
        doc_path.mkdir(parents=True, exist_ok=True)
        import shutil
        dest = doc_path / file_path.name
        shutil.copy2(str(file_path), str(dest))

        if self._minio_available:
            try:
                from minio import Minio
                client = Minio(
                    settings.storage_minio_endpoint,
                    access_key=settings.storage_minio_access_key,
                    secret_key=settings.storage_minio_secret_key,
                    secure=False,
                )
                object_name = f"{tender_id}/{doc_type}/{file_path.name}"
                client.fput_object(settings.storage_minio_bucket, object_name, str(dest))
                log.info("document_saved_to_minio", tender_id=tender_id, object_name=object_name)
            except Exception as e:
                log.warning("minio_save_failed", tender_id=tender_id, error=e)

        return True

    async def _save_to_pg(self, table: str, source: str, data: dict):
        if not self._pg_pool:
            return
        async with self._pg_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO raw_crawl_data (table_name, source, data, crawled_at)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (id) DO NOTHING""",
                table, source, json.dumps(data, default=str),
                datetime.now(timezone.utc),
            )

    async def close(self):
        if self._pg_pool:
            await self._pg_pool.close()


def save_raw_record(table: str, source: str, data: dict):
    file_path = OUTPUT_DIR / f"{table}.jsonl"
    record = {
        "source": source,
        "raw_data": data,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
    }
    with _get_lock(table):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")


def record_exists(table: str, key_field: str, key_value: str) -> bool:
    if not key_value:
        return False
    file_path = OUTPUT_DIR / f"{table}.jsonl"
    if not file_path.exists():
        return False
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("raw_data", {}).get(key_field) == key_value:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def read_all_records(table: str) -> List[dict]:
    file_path = OUTPUT_DIR / f"{table}.jsonl"
    if not file_path.exists():
        return []
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager
