"""add priority metadata to durable crawl frontier

Revision ID: 4d2e1c9b8a7f
Revises: 11c9f5a2d2aa
Create Date: 2026-04-18 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4d2e1c9b8a7f"
down_revision: Union[str, Sequence[str], None] = "11c9f5a2d2aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawl_frontier", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_frontier", sa.Column("predicted_page_type", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("discovered_from_page_type", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("discovery_reason", sa.String(), nullable=True))
    op.create_index(
        "ix_crawl_frontier_crawl_run_priority_depth_created",
        "crawl_frontier",
        ["crawl_run_id", "priority", "depth", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_frontier_crawl_run_priority_depth_created", table_name="crawl_frontier")
    op.drop_column("crawl_frontier", "discovery_reason")
    op.drop_column("crawl_frontier", "discovered_from_page_type")
    op.drop_column("crawl_frontier", "predicted_page_type")
    op.drop_column("crawl_frontier", "priority")
