from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict
from .config import settings


@dataclass
class MetricCounter:
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        if self.total == 0:
            return 0.0
        return self.total_duration_ms / self.total


@dataclass
class CrawlerMetrics:
    pages_crawled: MetricCounter = field(default_factory=MetricCounter)
    items_extracted: MetricCounter = field(default_factory=MetricCounter)
    items_saved: MetricCounter = field(default_factory=MetricCounter)
    items_downloaded: MetricCounter = field(default_factory=MetricCounter)
    items_validated: MetricCounter = field(default_factory=MetricCounter)
    items_deduplicated: MetricCounter = field(default_factory=MetricCounter)
    retry_attempts: int = 0
    captcha_detected: int = 0
    errors: Dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> dict:
        return {
            "pages_crawled": {
                "total": self.pages_crawled.total,
                "success": self.pages_crawled.success,
                "failed": self.pages_crawled.failed,
                "avg_duration_ms": round(self.pages_crawled.avg_duration_ms, 2),
            },
            "items_extracted": {
                "total": self.items_extracted.total,
                "success": self.items_extracted.success,
                "failed": self.items_extracted.failed,
            },
            "items_saved": self.items_saved.success,
            "items_downloaded": self.items_downloaded.success,
            "items_validated": self.items_validated.success,
            "items_deduplicated": {
                "duplicates_found": self.items_deduplicated.skipped,
                "unique": self.items_deduplicated.success,
            },
            "retry_attempts": self.retry_attempts,
            "captcha_detected": self.captcha_detected,
            "errors": self.errors,
        }

    def merge(self, other: "CrawlerMetrics"):
        for attr in ["pages_crawled", "items_extracted", "items_saved", "items_downloaded",
                     "items_validated", "items_deduplicated"]:
            ours = getattr(self, attr)
            theirs = getattr(other, attr)
            ours.total += theirs.total
            ours.success += theirs.success
            ours.failed += theirs.failed
            ours.skipped += theirs.skipped
            ours.total_duration_ms += theirs.total_duration_ms
        self.retry_attempts += other.retry_attempts
        self.captcha_detected += other.captcha_detected
        for k, v in other.errors.items():
            self.errors[k] = self.errors.get(k, 0) + v


_metrics = CrawlerMetrics()


def get_metrics() -> CrawlerMetrics:
    return _metrics


def reset_metrics():
    global _metrics
    _metrics = CrawlerMetrics()


@contextmanager
def track_duration(counter: MetricCounter):
    start = time.perf_counter()
    try:
        yield
        counter.success += 1
    except Exception:
        counter.failed += 1
        raise
    finally:
        counter.total += 1
        counter.total_duration_ms += (time.perf_counter() - start) * 1000


def record_error(error_type: str):
    _metrics.errors[error_type] = _metrics.errors.get(error_type, 0) + 1


def record_retry():
    _metrics.retry_attempts += 1


def record_captcha():
    _metrics.captcha_detected += 1
