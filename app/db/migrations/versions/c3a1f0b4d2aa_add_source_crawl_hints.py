"""add source crawl hints

Revision ID: c3a1f0b4d2aa
Revises: 2d4b8f6e1a9c
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3a1f0b4d2aa"
down_revision: Union[str, Sequence[str], None] = "2d4b8f6e1a9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sources", schema=None) as batch_op:
        batch_op.add_column(sa.Column("crawl_hints", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sources", schema=None) as batch_op:
        batch_op.drop_column("crawl_hints")
