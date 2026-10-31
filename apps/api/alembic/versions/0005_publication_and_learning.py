"""store publishing records, results and approved lessons on existing tables

Columns add no tablets, which matters on the sandbox cluster. Row-level security already covers both tables.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("publication", postgresql.JSONB))
    op.add_column("content_items", sa.Column("performance", postgresql.JSONB))
    op.add_column("brands", sa.Column("lessons", postgresql.JSONB))


def downgrade() -> None:
    op.drop_column("brands", "lessons")
    op.drop_column("content_items", "performance")
    op.drop_column("content_items", "publication")
