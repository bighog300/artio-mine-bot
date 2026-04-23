"""add records fingerprint_version column

Revision ID: 8d9a1c6b4e2f
Revises: f9c2e4a1b7d0
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8d9a1c6b4e2f"
down_revision = "f9c2e4a1b7d0"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if _has_column("records", "fingerprint_version"):
        return

    op.add_column(
        "records",
        sa.Column("fingerprint_version", sa.String(), nullable=False, server_default="v2"),
    )
    op.alter_column("records", "fingerprint_version", server_default=None)


def downgrade() -> None:
    if not _has_column("records", "fingerprint_version"):
        return

    op.drop_column("records", "fingerprint_version")
