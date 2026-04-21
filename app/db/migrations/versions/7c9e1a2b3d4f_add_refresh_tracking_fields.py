"""add refresh tracking fields to crawl_frontier

Revision ID: 7c9e1a2b3d4f
Revises: b2f7e91c4d11
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c9e1a2b3d4f"
down_revision: Union[str, Sequence[str], None] = "b2f7e91c4d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawl_frontier", sa.Column("last_change_detected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crawl_frontier", sa.Column("last_refresh_outcome", sa.String(), nullable=True))
    op.create_index(
        "ix_crawl_frontier_source_mapping_next_eligible",
        "crawl_frontier",
        ["source_id", "mapping_version_id", "next_eligible_fetch_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_frontier_source_mapping_next_eligible", table_name="crawl_frontier")
    op.drop_column("crawl_frontier", "last_refresh_outcome")
    op.drop_column("crawl_frontier", "last_change_detected_at")
