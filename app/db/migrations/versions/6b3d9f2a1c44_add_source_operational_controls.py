"""add source operational control columns

Revision ID: 6b3d9f2a1c44
Revises: f4b2c7d9e1aa
Create Date: 2026-04-15 00:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6b3d9f2a1c44"
down_revision: Union[str, Sequence[str], None] = "f4b2c7d9e1aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("operational_status", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE sources SET operational_status = 'idle' WHERE operational_status IS NULL"))
    op.alter_column("sources", "operational_status", nullable=False, server_default=sa.text("'idle'"))

    op.add_column("sources", sa.Column("crawl_intent", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE sources SET crawl_intent = 'site_root' WHERE crawl_intent IS NULL"))
    op.alter_column("sources", "crawl_intent", nullable=False, server_default=sa.text("'site_root'"))

    op.add_column("sources", sa.Column("max_pages", sa.Integer(), nullable=True))

    op.add_column("sources", sa.Column("queue_paused", sa.Boolean(), nullable=True))
    op.execute(sa.text("UPDATE sources SET queue_paused = false WHERE queue_paused IS NULL"))
    op.alter_column("sources", "queue_paused", nullable=False, server_default=sa.text("false"))


def downgrade() -> None:
    op.drop_column("sources", "queue_paused", if_exists=True)
    op.drop_column("sources", "max_pages", if_exists=True)
    op.drop_column("sources", "crawl_intent", if_exists=True)
    op.drop_column("sources", "operational_status", if_exists=True)
