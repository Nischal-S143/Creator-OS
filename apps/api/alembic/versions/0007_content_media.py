"""store generated image and video references on content_items

No index: creating one allocates new tablets, and the sandbox cluster is already close to its limit.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("media", postgresql.JSONB))


def downgrade() -> None:
    op.drop_column("content_items", "media")
