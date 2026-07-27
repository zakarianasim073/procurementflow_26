"""Phase 2: Document and Team Management Models"""

from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import enum

from .base import Base, TimestampMixin, UUIDMixin


class TeamRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Document(Base, TimestampMixin, UUIDMixin):
    """Document model for Phase 2 - stores tender document metadata"""
    __tablename__ = "phase2_documents"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tender_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extracted_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        Index("ix_phase2_documents_tender_type", "tender_id", "document_type"),
        Index("ix_phase2_documents_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.name}>"


class TeamMember(Base, TimestampMixin, UUIDMixin):
    """Team member model for Phase 2"""
    __tablename__ = "phase2_team_members"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[TeamRole] = mapped_column(
        SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False
    )
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    invited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_phase2_team_members_tenant_email", "tenant_id", "email"),
        Index("ix_phase2_team_members_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<TeamMember {self.email} ({self.role})>"


class Team(Base, TimestampMixin, UUIDMixin):
    """Team model for Phase 2 - One per tenant"""
    __tablename__ = "phase2_teams"

    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Team {self.name}>"
