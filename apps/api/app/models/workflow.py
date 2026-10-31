import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


def _brand_scope() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["organization_id", "brand_id"], ["brands.organization_id", "brands.id"])


class BrandDocument(TimestampMixin, Base):
    __tablename__ = "brand_documents"
    __table_args__ = (_brand_scope(),)

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class BrandProfile(TimestampMixin, Base):
    __tablename__ = "brand_profiles"
    __table_args__ = (
        _brand_scope(),
        UniqueConstraint("brand_id", "version", name="uq_brand_profiles_brand_id_version"),
        CheckConstraint("status IN ('proposed', 'approved', 'rejected', 'superseded')", name="status"),
        CheckConstraint("memory_status IN ('not_synced', 'synced', 'failed')", name="memory_status"),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="proposed")
    voice: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, nullable=False)
    content_pillars: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    restrictions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    source_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brand_documents.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    memory_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="not_synced")


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        _brand_scope(),
        UniqueConstraint("organization_id", "id", name="uq_campaigns_organization_id_id"),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str | None] = mapped_column(Text)
    simulation: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        _brand_scope(),
        ForeignKeyConstraint(
            ["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"]
        ),
        CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="status"),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    graph_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="running")
    model: Mapped[str | None] = mapped_column(String(100))
    error: Mapped[str | None] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    started_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignScenario(TimestampMixin, Base):
    __tablename__ = "campaign_scenarios"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"]
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    content_format: Mapped[str] = mapped_column(String(50), nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
