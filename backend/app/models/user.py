"""User model"""

from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
import enum

from .base import Base, TimestampMixin, UUIDMixin


class UserPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)
    plan: Mapped[UserPlan] = mapped_column(
        SQLEnum(UserPlan), default=UserPlan.FREE, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gpt_quota_used: Mapped[int] = mapped_column(default=0, nullable=False)
    gpt_quota_limit: Mapped[int] = mapped_column(default=50000, nullable=False)

    # Relationships
    tenders: Mapped[List["Tender"]] = relationship("Tender", back_populates="owner", lazy="selectin")
    boq_comparisons: Mapped[List["BOQComparison"]] = relationship("BOQComparison", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class RefreshToken(Base, TimestampMixin, UUIDMixin):
    """Server-side refresh-token record (SEC-03/T-016, ADR-007).

    Stores only a SHA-256 hash of the token. `family_id` groups a rotation
    chain; presenting an already-rotated token revokes the whole family
    (reuse detection).
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_refresh_tokens_family_active", "family_id", "revoked_at"),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken {self.id} family={self.family_id}>"
