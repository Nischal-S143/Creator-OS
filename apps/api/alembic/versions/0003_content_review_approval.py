"""add content versions, guardian reviews and approvals

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _uuid(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _pk() -> sa.Column:
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _content_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id", "content_id"],
        ["content_items.organization_id", "content_items.id"],
        name=f"fk_{table}_content",
    )


def upgrade() -> None:
    op.create_table(
        "content_items",
        _pk(),
        _uuid("organization_id"),
        _uuid("brand_id"),
        _uuid("campaign_id"),
        _uuid("scenario_id"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="organic"),
        sa.Column("status", sa.String(30), nullable=False, server_default="generating"),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="0"),
        _uuid("created_by"),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_content_items"),
        sa.ForeignKeyConstraint(
            ["organization_id", "brand_id"],
            ["brands.organization_id", "brands.id"],
            name="fk_content_items_brand",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "campaign_id"],
            ["campaigns.organization_id", "campaigns.id"],
            name="fk_content_items_campaign",
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["campaign_scenarios.id"], name="fk_content_items_scenario"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_content_items_created_by_users"),
        sa.UniqueConstraint("organization_id", "id", name="uq_content_items_organization_id_id"),
        sa.CheckConstraint("kind IN ('organic', 'ad')", name="ck_content_items_kind"),
        sa.CheckConstraint(
            "status IN ('generating', 'failed', 'blocked', 'in_review', 'changes_requested', 'approved')",
            name="ck_content_items_status",
        ),
    )
    op.create_index("ix_content_items_brand_id", "content_items", ["brand_id"])
    op.create_index("ix_content_items_campaign_id", "content_items", ["campaign_id"])

    op.create_table(
        "content_versions",
        _pk(),
        _uuid("organization_id"),
        _uuid("content_id"),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("hook", sa.Text, nullable=False),
        sa.Column("script", sa.Text, nullable=False),
        sa.Column("caption", sa.Text, nullable=False),
        sa.Column("cta", sa.Text, nullable=False),
        sa.Column("hashtags", postgresql.JSONB, nullable=False),
        sa.Column("scene_plan", postgresql.JSONB, nullable=False),
        sa.Column("research", postgresql.JSONB, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        _uuid("created_by"),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_content_versions"),
        _content_fk("content_versions"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_content_versions_created_by_users"),
        sa.UniqueConstraint("content_id", "version", name="uq_content_versions_content_id_version"),
        sa.CheckConstraint("source IN ('agent', 'human')", name="ck_content_versions_source"),
    )
    op.create_index("ix_content_versions_content_id", "content_versions", ["content_id"])

    op.create_table(
        "guardian_reviews",
        _pk(),
        _uuid("organization_id"),
        _uuid("content_id"),
        sa.Column("content_version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("findings", postgresql.JSONB, nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_guardian_reviews"),
        _content_fk("guardian_reviews"),
        sa.CheckConstraint(
            "status IN ('PASS', 'NEEDS_REVIEW', 'BLOCKED')", name="ck_guardian_reviews_status"
        ),
    )
    op.create_index("ix_guardian_reviews_content_id", "guardian_reviews", ["content_id"])

    op.create_table(
        "approvals",
        _pk(),
        _uuid("organization_id"),
        _uuid("content_id"),
        sa.Column("content_version", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("feedback", sa.Text),
        _uuid("reviewed_by", nullable=True),
        _created_at(),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_approvals"),
        _content_fk("approvals"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_approvals_reviewed_by_users"),
        sa.CheckConstraint(
            "decision IN ('pending', 'approved', 'changes_requested', 'superseded')",
            name="ck_approvals_decision",
        ),
    )
    op.create_index("ix_approvals_organization_id", "approvals", ["organization_id"])
    op.create_index("ix_approvals_content_id", "approvals", ["content_id"])

    scope = f"organization_id = {TENANT}"
    op.execute("ALTER TABLE content_items ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY content_items_tenant ON content_items FOR ALL USING ({scope}) WITH CHECK ({scope})"
    )

    # Immutable history: read and insert only, so the database itself refuses edits and deletes.
    for table in ("content_versions", "guardian_reviews"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({scope})")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({scope})")

    # An approval can change only while pending.
    op.execute("ALTER TABLE approvals ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY approvals_select ON approvals FOR SELECT USING ({scope})")
    op.execute(f"CREATE POLICY approvals_insert ON approvals FOR INSERT WITH CHECK ({scope})")
    op.execute(
        f"CREATE POLICY approvals_update ON approvals FOR UPDATE "
        f"USING ({scope} AND decision = 'pending') WITH CHECK ({scope})"
    )


def downgrade() -> None:
    for table in ("approvals", "guardian_reviews", "content_versions", "content_items"):
        op.drop_table(table)
