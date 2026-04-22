"""add missing source columns for current ORM model

Revision ID: f4b2c7d9e1aa
Revises: e8f1c2d3b4a5
Create Date: 2026-04-15 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f4b2c7d9e1aa"
down_revision: Union[str, Sequence[str], None] = "e8f1c2d3b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("extraction_rules", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("max_depth", sa.Integer(), nullable=True))

    op.add_column("sources", sa.Column("enabled", sa.Boolean(), nullable=True))
    op.execute(sa.text("UPDATE sources SET enabled = true WHERE enabled IS NULL"))
    op.alter_column("sources", "enabled", nullable=False, server_default=sa.text("true"))

    op.add_column("sources", sa.Column("health_status", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE sources SET health_status = 'unknown' WHERE health_status IS NULL"))
    op.alter_column("sources", "health_status", nullable=False, server_default=sa.text("'unknown'"))


def downgrade() -> None:
    op.drop_column("sources", "health_status", if_exists=True)
    op.drop_column("sources", "enabled", if_exists=True)
    op.drop_column("sources", "max_depth", if_exists=True)
    op.drop_column("sources", "extraction_rules", if_exists=True)
