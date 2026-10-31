import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

ROLES = ("owner", "admin", "manager", "editor", "analyst", "client_approver")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    auth_provider_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Stored lowercase.
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)


class Organization(TimestampMixin, Base):
    """Tenant root. organizations.id is the tenant id for every tenant-owned table."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, server_default="free")
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class Membership(TimestampMixin, Base):
    """Memberships are marked removed, never deleted: brands reference them for ownership."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_memberships_organization_id_user_id"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'manager', 'editor', 'analyst', 'client_approver')", name="role"
        ),
        CheckConstraint("status IN ('active', 'removed')", name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
