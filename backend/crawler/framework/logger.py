from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from .config import settings


_LOG_RECORD_CACHE: Dict[str, Any] = {}
_SENSITIVE_KEYS = {"password", "secret", "token", "authorization", "cookie", "content", "body"}


def _redact(value: Any, key: str = "") -> Any:
    if any(part in key.lower() for part in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _get_or_create_request_id() -> str:
    if "request_id" not in _LOG_RECORD_CACHE:
        _LOG_RECORD_CACHE["request_id"] = str(uuid4())[:8]
    return _LOG_RECORD_CACHE["request_id"]


class StructuredLogger:
    def __init__(self, name: str, output_file: Optional[Path] = None):
        self.name = name
        self.request_id = _get_or_create_request_id()
        self._file = output_file or (
            Path(settings.log_file) if settings.log_file else None
        )
        if self._file:
            self._file.parent.mkdir(parents=True, exist_ok=True)

    def _log(
        self,
        level: str,
        event: str,
        *,
        error: Optional[Exception] = None,
        **kwargs,
    ):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "logger": self.name,
            "event": event,
            "request_id": self.request_id,
            **_redact(kwargs),
        }
        if error:
            record["error"] = str(error)
            record["error_type"] = type(error).__name__

        message = json.dumps(record, default=str, ensure_ascii=False)

        if settings.log_json_format and self._file:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        else:
            print(message, file=sys.stderr)

    def debug(self, event: str, **kwargs):
        if settings.log_level.value == "DEBUG":
            self._log("DEBUG", event, **kwargs)

    def info(self, event: str, **kwargs):
        if settings.log_level.value in ("DEBUG", "INFO"):
            self._log("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs):
        self._log("WARNING", event, **kwargs)

    def error(self, event: str, error: Optional[Exception] = None, **kwargs):
        self._log("ERROR", event, error=error, **kwargs)

    def critical(self, event: str, error: Optional[Exception] = None, **kwargs):
        self._log("CRITICAL", event, error=error, **kwargs)


_instances: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    if name not in _instances:
        _instances[name] = StructuredLogger(name)
    return _instances[name]


class CrawlerLogRecord:
    def __init__(self, plugin: str, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid4())[:12]
        self.plugin = plugin
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.status: str = "pending"
        self.pages_done: int = 0
        self.items_done: int = 0
        self.items_skipped: int = 0
        self.items_failed: int = 0
        self.error: Optional[str] = None
        self.log = get_logger(f"crawl.{plugin}")

    def start(self):
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.status = "running"
        self.log.info("crawl_started", plugin=self.plugin, run_id=self.run_id)

    def progress(self, pages_done: int = 0, items_done: int = 0, items_skipped: int = 0, items_failed: int = 0):
        self.pages_done = pages_done or self.pages_done
        self.items_done = items_done or self.items_done
        self.items_skipped = items_skipped or self.items_skipped
        self.items_failed = items_failed or self.items_failed

    def finish(self, status: str = "success", error: Optional[str] = None):
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.status = status
        self.error = error
        log_method = self.log.error if error else self.log.info
        log_method(
            "crawl_finished",
            plugin=self.plugin,
            run_id=self.run_id,
            status=status,
            pages_done=self.pages_done,
            items_done=self.items_done,
            items_skipped=self.items_skipped,
            items_failed=self.items_failed,
            error=error,
        )

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "plugin": self.plugin,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "pages_done": self.pages_done,
            "items_done": self.items_done,
            "items_skipped": self.items_skipped,
            "items_failed": self.items_failed,
            "error": self.error,
        }
