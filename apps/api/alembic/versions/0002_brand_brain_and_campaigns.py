"""add brand documents, profiles, campaigns, agent runs and scenarios

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
TABLES = ("brand_documents", "brand_profiles", "campaigns", "agent_runs", "campaign_scenarios")


def _uuid(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _pk() -> sa.Column:
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _brand_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id", "brand_id"],
        ["brands.organization_id", "brands.id"],
        name=f"fk_{table}_brand",
    )


def _campaign_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id", "campaign_id"],
        ["campaigns.organization_id", "campaigns.id"],
        name=f"fk_{table}_campaign",
    )


def upgrade() -> None:
    op.create_table(
        "brand_documents",
        _pk(),
        _uuid("organization_id"),
        _uuid("brand_id"),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("extracted_text", sa.Text, nullable=False),
        _uuid("uploaded_by"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_brand_documents"),
        _brand_fk("brand_documents"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name="fk_brand_documents_uploaded_by_users"),
    )
    op.create_index("ix_brand_documents_brand_id", "brand_documents", ["brand_id"])

    op.create_table(
        "brand_profiles",
        _pk(),
        _uuid("organization_id"),
        _uuid("brand_id"),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("voice", sa.Text, nullable=False),
        sa.Column("tone", sa.Text, nullable=False),
        sa.Column("audience", sa.Text, nullable=False),
        sa.Column("content_pillars", postgresql.JSONB, nullable=False),
        sa.Column("restrictions", postgresql.JSONB, nullable=False),
        _uuid("source_document_id"),
        _uuid("created_by"),
        _uuid("decided_by", nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("memory_status", sa.String(20), nullable=False, server_default="not_synced"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_brand_profiles"),
        _brand_fk("brand_profiles"),
        sa.UniqueConstraint("brand_id", "version", name="uq_brand_profiles_brand_id_version"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["brand_documents.id"], name="fk_brand_profiles_source_document"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_brand_profiles_created_by_users"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], name="fk_brand_profiles_decided_by_users"),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected', 'superseded')", name="ck_brand_profiles_status"
        ),
        sa.CheckConstraint(
            "memory_status IN ('not_synced', 'synced', 'failed')", name="ck_brand_profiles_memory_status"
        ),
    )
    op.create_index("ix_brand_profiles_brand_id", "brand_profiles", ["brand_id"])

    op.create_table(
        "campaigns",
        _pk(),
        _uuid("organization_id"),
        _uuid("brand_id"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("audience", sa.Text),
        _uuid("created_by"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_campaigns"),
        _brand_fk("campaigns"),
        sa.UniqueConstraint("organization_id", "id", name="uq_campaigns_organization_id_id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_campaigns_created_by_users"),
    )
    op.create_index("ix_campaigns_brand_id", "campaigns", ["brand_id"])

    op.create_table(
        "agent_runs",
        _pk(),
        _uuid("organization_id"),
        _uuid("brand_id"),
        _uuid("campaign_id", nullable=True),
        sa.Column("graph_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("model", sa.String(100)),
        sa.Column("error", sa.String(100)),
        sa.Column("detail", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        _uuid("started_by"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
        _brand_fk("agent_runs"),
        _campaign_fk("agent_runs"),
        sa.ForeignKeyConstraint(["started_by"], ["users.id"], name="fk_agent_runs_started_by_users"),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="ck_agent_runs_status"),
    )
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])
    op.create_index("ix_agent_runs_campaign_id", "agent_runs", ["campaign_id"])

    op.create_table(
        "campaign_scenarios",
        _pk(),
        _uuid("organization_id"),
        _uuid("campaign_id"),
        _uuid("agent_run_id"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("hook", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("content_format", sa.String(50), nullable=False),
        sa.Column("selected", sa.Boolean, nullable=False, server_default=sa.text("false")),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_campaign_scenarios"),
        _campaign_fk("campaign_scenarios"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], name="fk_campaign_scenarios_agent_run"),
    )
    op.create_index("ix_campaign_scenarios_campaign_id", "campaign_scenarios", ["campaign_id"])

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant ON {table} FOR ALL "
            f"USING (organization_id = {TENANT}) WITH CHECK (organization_id = {TENANT})"
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
