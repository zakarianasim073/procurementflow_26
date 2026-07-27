from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CrawlMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL = "full"
    VERIFY = "verify"
    RESUME = "resume"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StorageBackend(str, Enum):
    JSONL = "jsonl"
    POSTGRESQL = "postgresql"
    MINIO = "minio"
    BOTH = "both"


class CrawlerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_concurrent_contexts: int = Field(default=4)
    rate_limit_seconds: float = Field(default=2.0)

    browser_headless: bool = Field(default=True)
    browser_viewport_width: int = Field(default=1280)
    browser_viewport_height: int = Field(default=900)
    browser_timeout_ms: int = Field(default=30000)
    browser_navigation_timeout_ms: int = Field(default=60000)
    browser_max_contexts: int = Field(default=4)
    browser_max_retries: int = Field(default=3)
    browser_recovery_delay_s: float = Field(default=5.0)
    browser_stealth: bool = Field(default=True)

    rate_limit_min_s: float = Field(default=1.0)
    rate_limit_max_s: float = Field(default=3.0)
    rate_limit_per_domain: bool = Field(default=True)

    retry_max_attempts: int = Field(default=3)
    retry_base_delay_s: float = Field(default=2.0)
    retry_max_delay_s: float = Field(default=30.0)

    storage_backend: StorageBackend = Field(default=StorageBackend.BOTH)
    storage_output_dir: str = Field(default="output/raw")
    storage_postgres_url: Optional[str] = Field(default=None)
    storage_minio_endpoint: Optional[str] = Field(default=None)
    storage_minio_bucket: str = Field(default="crawler-docs")
    storage_minio_access_key: Optional[str] = Field(default=None)
    storage_minio_secret_key: Optional[str] = Field(default=None)
    storage_chunk_size_mb: int = Field(default=10)

    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_json_format: bool = Field(default=True)
    log_file: Optional[str] = Field(default="output/logs/crawler.jsonl")

    metrics_enabled: bool = Field(default=False)
    metrics_port: int = Field(default=9100)

    scheduler_enabled: bool = Field(default=True)
    scheduler_daily_at: str = Field(default="06:00")
    scheduler_weekly_verify_day: str = Field(default="monday")

    proxy_enabled: bool = Field(default=False)
    proxy_url: Optional[str] = Field(default=None)
    proxy_rotation: bool = Field(default=False)
    proxy_list: List[str] = Field(default_factory=list)
    proxy_health_check_url: str = Field(default="https://www.eprocure.gov.bd")
    proxy_health_check_timeout_s: float = Field(default=10.0)

    captcha_detect_enabled: bool = Field(default=True)
    captcha_solver_service: Optional[str] = Field(default=None)

    checkpoint_enabled: bool = Field(default=True)
    checkpoint_dir: str = Field(default="output/checkpoints")

    download_temp_dir: str = Field(default="output/downloads/temp")
    download_max_size_mb: int = Field(default=200)
    download_allowed_types: List[str] = Field(
        default=["pdf", "zip", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "tif", "tiff"]
    )

    dedup_enabled: bool = Field(default=True)
    dedup_hash_fields: List[str] = Field(default=["id", "url"])
    dedup_use_content_hash: bool = Field(default=True)

    change_detection_enabled: bool = Field(default=True)
    version_history_enabled: bool = Field(default=True)
    version_history_max_versions: int = Field(default=10)

    max_workers: int = Field(default=2)
    worker_queue_size: int = Field(default=100)
    worker_poll_interval_s: float = Field(default=1.0)

    e_gp_base_url: str = Field(default="https://www.eprocure.gov.bd")
    e_gp_email: Optional[str] = Field(default=None)
    e_gp_password: Optional[str] = Field(default=None)

    bppa_base_url: str = Field(default="https://www.bppa.gov.bd")

    @field_validator("storage_postgres_url")
    @classmethod
    def validate_db_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("postgresql"):
            raise ValueError("storage_postgres_url must start with 'postgresql'")
        return v

    @property
    def output_dir(self) -> Path:
        return Path(self.storage_output_dir)

    @property
    def checkpoint_path(self) -> Path:
        return Path(self.checkpoint_dir)

    @property
    def download_temp_path(self) -> Path:
        return Path(self.download_temp_dir)

    def url(self, path: str) -> str:
        """Join the e-GP base URL with a path safely (handles missing/extra slashes)."""
        base = self.e_gp_base_url.rstrip("/")
        if not path:
            return base
        return base + "/" + path.lstrip("/")

    def ensure_dirs(self):
        for p in [self.output_dir, self.checkpoint_path, self.download_temp_path, Path("output/logs")]:
            p.mkdir(parents=True, exist_ok=True)


settings = CrawlerSettings()

BASE_URL = settings.e_gp_base_url + "/resources/common/"
BPPA_URL = settings.bppa_base_url
