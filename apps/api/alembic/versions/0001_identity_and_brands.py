"""create identity and brand tables with row-level security

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
CURRENT_USER_ID = "NULLIF(current_setting('app.user_id', true), '')::uuid"
SUBJECT = "NULLIF(current_setting('app.auth_subject', true), '')"


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )


def _uuid(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("auth_provider_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("auth_provider_id", name="uq_users_auth_provider_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "organizations",
        _uuid_pk(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        _uuid("owner_id"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_organizations_owner_id_users"),
    )
    op.create_index("ix_organizations_owner_id", "organizations", ["owner_id"])

    op.create_table(
        "memberships",
        _uuid_pk(),
        _uuid("organization_id"),
        _uuid("user_id"),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_memberships_organization_id_user_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_memberships_organization_id_organizations"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_memberships_user_id_users"),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'manager', 'editor', 'analyst', 'client_approver')",
            name="ck_memberships_role",
        ),
        sa.CheckConstraint("status IN ('active', 'removed')", name="ck_memberships_status"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "brands",
        _uuid_pk(),
        _uuid("organization_id"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("industry", sa.String(100)),
        sa.Column("website_url", sa.String(2048)),
        sa.Column("meko_datapack_id", sa.String(255)),
        _uuid("owner_id"),
        _uuid("created_by"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_brands"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_brands_organization_id_slug"),
        sa.UniqueConstraint("organization_id", "id", name="uq_brands_organization_id_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_brands_organization_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "owner_id"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_brands_owner_membership",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_brands_created_by_users"),
    )
    op.create_index("ix_brands_organization_id", "brands", ["organization_id"])
    op.create_index("ix_brands_owner_id", "brands", ["owner_id"])

    for table in ("users", "organizations", "memberships", "brands"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    is_me = f"(auth_provider_id = {SUBJECT} OR id = {CURRENT_USER_ID})"
    op.execute(f"""
        CREATE POLICY users_select ON users FOR SELECT USING (
            {is_me} OR EXISTS (
                SELECT 1 FROM memberships m
                WHERE m.user_id = users.id AND m.organization_id = {TENANT}
            )
        )
    """)
    op.execute(f"CREATE POLICY users_insert ON users FOR INSERT WITH CHECK (auth_provider_id = {SUBJECT})")
    op.execute(f"CREATE POLICY users_update ON users FOR UPDATE USING ({is_me}) WITH CHECK ({is_me})")

    op.execute(f"""
        CREATE POLICY organizations_select ON organizations FOR SELECT USING (
            id = {TENANT} OR EXISTS (
                SELECT 1 FROM memberships m
                WHERE m.organization_id = organizations.id
                  AND m.user_id = {CURRENT_USER_ID} AND m.status = 'active'
            )
        )
    """)
    op.execute(f"CREATE POLICY organizations_insert ON organizations FOR INSERT WITH CHECK (id = {TENANT})")
    op.execute(
        f"CREATE POLICY organizations_update ON organizations FOR UPDATE "
        f"USING (id = {TENANT}) WITH CHECK (id = {TENANT})"
    )

    op.execute(f"""
        CREATE POLICY memberships_select ON memberships FOR SELECT USING (
            organization_id = {TENANT} OR user_id = {CURRENT_USER_ID}
        )
    """)
    op.execute(
        f"CREATE POLICY memberships_insert ON memberships FOR INSERT WITH CHECK (organization_id = {TENANT})"
    )
    op.execute(
        f"CREATE POLICY memberships_update ON memberships FOR UPDATE "
        f"USING (organization_id = {TENANT}) WITH CHECK (organization_id = {TENANT})"
    )

    op.execute(
        f"CREATE POLICY brands_tenant ON brands FOR ALL "
        f"USING (organization_id = {TENANT}) WITH CHECK (organization_id = {TENANT})"
    )

    # Adding a member needs a lookup across tenants. This returns only the id for an exact email.
    schema = op.get_bind().execute(sa.text("SELECT current_schema()")).scalar_one()
    op.execute(f"""
        CREATE FUNCTION find_user_id_by_email(lookup_email text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, "{schema}"
        AS $$ SELECT id FROM users WHERE email = lower(lookup_email) $$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION find_user_id_by_email(text)")
    # These policies read memberships, so they must go before the table does.
    op.execute("DROP POLICY users_select ON users")
    op.execute("DROP POLICY organizations_select ON organizations")
    op.drop_table("brands")
    op.drop_table("memberships")
    op.drop_table("organizations")
    op.drop_table("users")
