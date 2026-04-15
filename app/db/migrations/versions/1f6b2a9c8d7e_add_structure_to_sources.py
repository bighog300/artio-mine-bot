"""add structure analysis columns to sources

Revision ID: 1f6b2a9c8d7e
Revises: 6b3d9f2a1c44
Create Date: 2026-04-15 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1f6b2a9c8d7e"
down_revision: Union[str, Sequence[str], None] = "6b3d9f2a1c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("structure_map", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("structure_status", sa.String(length=50), nullable=True))
    op.execute(sa.text("UPDATE sources SET structure_status = 'pending' WHERE structure_status IS NULL"))
    op.alter_column("sources", "structure_status", nullable=False, server_default=sa.text("'pending'"))
    op.add_column("sources", sa.Column("structure_error", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "analyzed_at")
    op.drop_column("sources", "structure_error")
    op.drop_column("sources", "structure_status")
    op.drop_column("sources", "structure_map")
