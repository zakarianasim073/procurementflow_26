from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import settings
from .logger import get_logger

log = get_logger("crawler.deduplicator")


class Deduplicator:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or settings.checkpoint_path / "dedup"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._seen_keys: Dict[str, Set[str]] = {}
        self._content_hashes: Set[str] = set()

    def _load_cache(self, table: str) -> Set[str]:
        if table not in self._seen_keys:
            cache_file = self.cache_dir / f"{table}_keys.json"
            self._seen_keys[table] = set()
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        self._seen_keys[table] = set(json.load(f))
                except (json.JSONDecodeError, IOError):
                    pass
        return self._seen_keys[table]

    def _save_cache(self, table: str):
        if table in self._seen_keys:
            cache_file = self.cache_dir / f"{table}_keys.json"
            try:
                with open(cache_file, "w") as f:
                    json.dump(list(self._seen_keys[table]), f)
            except IOError as e:
                log.warning("dedup_cache_save_failed", table=table, error=e)

    def is_duplicate(self, table: str, record: Dict[str, Any]) -> bool:
        if not settings.dedup_enabled:
            return False
        dedup_key = self._build_key(table, record)
        seen = self._load_cache(table)
        if dedup_key in seen:
            return True
        if settings.dedup_use_content_hash:
            content_hash = self._content_hash(record)
            if content_hash in self._content_hashes:
                return True
        return False

    def mark_seen(self, table: str, record: Dict[str, Any]):
        if not settings.dedup_enabled:
            return
        dedup_key = self._build_key(table, record)
        seen = self._load_cache(table)
        seen.add(dedup_key)
        if settings.dedup_use_content_hash:
            content_hash = self._content_hash(record)
            self._content_hashes.add(content_hash)
        if len(seen) % 100 == 0:
            self._save_cache(table)

    def flush(self):
        for table in list(self._seen_keys.keys()):
            self._save_cache(table)

    def _build_key(self, table: str, record: Dict[str, Any]) -> str:
        parts = []
        for field in settings.dedup_hash_fields:
            value = record.get(field) or record.get("raw_data", {}).get(field)
            if value:
                parts.append(str(value))
        if not parts:
            content = json.dumps(record, sort_keys=True, default=str)
            return hashlib.md5(content.encode()).hexdigest()
        return ":".join(parts)

    def _content_hash(self, record: Dict[str, Any]) -> str:
        content = json.dumps(record, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()


_deduplicator: Optional[Deduplicator] = None


def get_deduplicator() -> Deduplicator:
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = Deduplicator()
    return _deduplicator
