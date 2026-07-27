"""Messaging models — AgentBrain messages, logs, and job queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentBrainMessage(Base):
    """Inter-agent communication messages (Agent Brain)."""

    __tablename__ = "agent_brain_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sender_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    message_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    response_to: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<AgentBrainMessage {self.id}: {self.subject}>"


class AgentLog(Base):
    """Agent execution logs."""

    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_results.id"), nullable=True, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(10), default="INFO", nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<AgentLog {self.id}: {self.level}>"


class AgentJob(Base):
    """Agent job queue."""

    __tablename__ = "agent_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_agent_jobs_agent_id", "agent_id"),
        Index("ix_agent_jobs_request_id", "request_id"),
        Index("ix_agent_jobs_tender_id", "tender_id"),
    )

    def __repr__(self) -> str:
        return f"<AgentJob {self.id}: {self.agent_id} state={self.state}>"
