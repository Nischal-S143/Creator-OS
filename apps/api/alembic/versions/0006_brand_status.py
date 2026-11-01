"""add a status column to brands so a client can be archived (soft-deleted)

No index is added: creating one allocates new tablets, and the sandbox cluster is already close to
its tablet limit (see docs/architecture.md). Row-level security already covers this table.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brands", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.create_check_constraint("ck_brands_status", "brands", "status IN ('active', 'archived')")


def downgrade() -> None:
    op.drop_constraint("ck_brands_status", "brands", type_="check")
    op.drop_column("brands", "status")
