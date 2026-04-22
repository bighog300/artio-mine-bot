"""finalize crawler reliability guarantees

Revision ID: 1a2b3c4d5e6f
Revises: 0f9e8d7c6b5a
Create Date: 2026-04-22 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "0f9e8d7c6b5a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("crawl_frontier") as batch_op:
        batch_op.add_column(sa.Column("lease_version", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE crawl_frontier SET lease_version = 0 WHERE lease_version IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("crawl_frontier") as batch_op:
        batch_op.drop_column("retry_after")
        batch_op.drop_column("lease_version")
