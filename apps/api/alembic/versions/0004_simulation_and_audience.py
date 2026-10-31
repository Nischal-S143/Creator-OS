"""store flight simulator results and audience reports on existing tables

Columns add no tablets, which matters on the sandbox cluster. Row-level security already covers both tables.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("simulation", postgresql.JSONB))
    op.add_column("brands", sa.Column("audience_report", postgresql.JSONB))


def downgrade() -> None:
    op.drop_column("brands", "audience_report")
    op.drop_column("campaigns", "simulation")
