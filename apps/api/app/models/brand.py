import uuid

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_brands_organization_id_slug"),
        # Lets child tables use composite foreign keys, so they cannot reference another tenant's brand.
        UniqueConstraint("organization_id", "id", name="uq_brands_organization_id_id"),
        # The owner must belong to this brand's organization.
        ForeignKeyConstraint(
            ["organization_id", "owner_id"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_brands_owner_membership",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100))
    website_url: Mapped[str | None] = mapped_column(String(2048))
    # Set only by the backend. Never accepted from API requests.
    meko_datapack_id: Mapped[str | None] = mapped_column(String(255))
    audience_report: Mapped[dict | None] = mapped_column(JSONB)
    lessons: Mapped[list | None] = mapped_column(JSONB)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
