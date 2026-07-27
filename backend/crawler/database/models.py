from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, BigInteger,
    Boolean, Index, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    plugin: Mapped[str] = mapped_column(String(100))
    run_id: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[datetime] = mapped_column(nullable=True)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)
    pages_done: Mapped[int] = mapped_column(default=0)
    items_done: Mapped[int] = mapped_column(default=0)
    items_skipped: Mapped[int] = mapped_column(default=0)
    items_failed: Mapped[int] = mapped_column(default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_crawl_jobs_plugin", "plugin"),
        Index("ix_crawl_jobs_status", "status"),
    )


class CrawlCheckpoint(Base):
    __tablename__ = "crawl_checkpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    plugin: Mapped[str] = mapped_column(String(100))
    checkpoint_key: Mapped[str] = mapped_column(String(200))
    data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("plugin", "checkpoint_key", name="uq_plugin_checkpoint"),
        Index("ix_checkpoint_plugin", "plugin"),
    )


class RawCrawlData(Base):
    __tablename__ = "raw_crawl_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(100))
    data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    data_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_raw_data_table", "table_name"),
        Index("ix_raw_data_source", "source"),
        Index("ix_raw_data_crawled", "crawled_at"),
        Index("ix_raw_data_hash", "data_hash"),
    )


class CrawlDocument(Base):
    __tablename__ = "crawl_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[str] = mapped_column(String(50))
    doc_type: Mapped[str] = mapped_column(String(50))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(default=0)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    minio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    downloaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    doc_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_doc_tender_id", "tender_id"),
        Index("ix_doc_type", "doc_type"),
    )


class CrawlChangeLog(Base):
    __tablename__ = "crawl_change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100))
    record_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    change_type: Mapped[str] = mapped_column(String(20))
    previous_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    changed_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_change_log_table", "table_name"),
        Index("ix_change_log_time", "detected_at"),
    )


class CrawlError(Base):
    __tablename__ = "crawl_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    plugin: Mapped[str] = mapped_column(String(100))
    error_type: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_error_plugin", "plugin"),
        Index("ix_error_type", "error_type"),
    )


SCHEMA_SQL = """
-- Raw crawl data table
CREATE TABLE IF NOT EXISTS raw_crawl_data (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    data_hash VARCHAR(64),
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_raw_data_table ON raw_crawl_data(table_name);
CREATE INDEX IF NOT EXISTS ix_raw_data_crawled ON raw_crawl_data(crawled_at);
CREATE INDEX IF NOT EXISTS ix_raw_data_hash ON raw_crawl_data(data_hash);

-- Crawl jobs for tracking
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id BIGSERIAL PRIMARY KEY,
    plugin VARCHAR(100) NOT NULL,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    pages_done INT DEFAULT 0,
    items_done INT DEFAULT 0,
    items_skipped INT DEFAULT 0,
    items_failed INT DEFAULT 0,
    error TEXT,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_crawl_jobs_plugin ON crawl_jobs(plugin);
CREATE INDEX IF NOT EXISTS ix_crawl_jobs_status ON crawl_jobs(status);

-- Checkpoints for resume capability
CREATE TABLE IF NOT EXISTS crawl_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    plugin VARCHAR(100) NOT NULL,
    checkpoint_key VARCHAR(200) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plugin, checkpoint_key)
);

-- Documents downloaded
CREATE TABLE IF NOT EXISTS crawl_documents (
    id BIGSERIAL PRIMARY KEY,
    tender_id VARCHAR(50) NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_hash VARCHAR(64),
    source_url TEXT,
    minio_path VARCHAR(500),
    downloaded_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS ix_doc_tender_id ON crawl_documents(tender_id);

-- Change log for version history
CREATE TABLE IF NOT EXISTS crawl_change_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100),
    change_type VARCHAR(20) NOT NULL,
    previous_data JSONB,
    new_data JSONB,
    changed_fields JSONB,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Error tracking
CREATE TABLE IF NOT EXISTS crawl_errors (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(50),
    plugin VARCHAR(100) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    url TEXT,
    traceback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
