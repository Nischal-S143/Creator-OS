import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def _content_scope() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["organization_id", "content_id"], ["content_items.organization_id", "content_items.id"]
    )


class ContentItem(TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "brand_id"], ["brands.organization_id", "brands.id"]),
        ForeignKeyConstraint(
            ["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"]
        ),
        UniqueConstraint("organization_id", "id", name="uq_content_items_organization_id_id"),
        CheckConstraint("kind IN ('organic', 'ad')", name="kind"),
        CheckConstraint(
            "status IN ('generating', 'failed', 'blocked', 'in_review', 'changes_requested', 'approved')",
            name="status",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaign_scenarios.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="organic")
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="generating")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class ContentVersion(Base):
    """Immutable. The database gives the app role no way to update or delete these rows."""

    __tablename__ = "content_versions"
    __table_args__ = (
        _content_scope(),
        UniqueConstraint("content_id", "version", name="uq_content_versions_content_id_version"),
        CheckConstraint("source IN ('agent', 'human')", name="source"),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    scene_plan: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    research: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GuardianReview(Base):
    """Immutable, like content versions."""

    __tablename__ = "guardian_reviews"
    __table_args__ = (
        _content_scope(),
        CheckConstraint("status IN ('PASS', 'NEEDS_REVIEW', 'BLOCKED')", name="status"),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    findings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Approval(Base):
    """A decision on one exact version. Once decided, the database refuses further changes."""

    __tablename__ = "approvals"
    __table_args__ = (
        _content_scope(),
        CheckConstraint(
            "decision IN ('pending', 'approved', 'changes_requested', 'superseded')", name="decision"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    feedback: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
