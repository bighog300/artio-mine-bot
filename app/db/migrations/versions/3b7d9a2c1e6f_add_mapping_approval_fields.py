"""add mapping approval lifecycle fields

Revision ID: 3b7d9a2c1e6f
Revises: 2a4b6c8d9e0f
Create Date: 2026-04-21 02:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b7d9a2c1e6f"
down_revision: Union[str, Sequence[str], None] = "2a4b6c8d9e0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("source_mapping_versions", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column("source_mapping_versions", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "source_mapping_versions",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("source_mapping_versions", sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("source_mapping_versions", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("source_mapping_versions", "superseded_at", if_exists=True)
    op.drop_column("source_mapping_versions", "is_active", if_exists=True)
    op.drop_column("source_mapping_versions", "approved_at", if_exists=True)
    op.drop_column("source_mapping_versions", "approved_by", if_exists=True)
