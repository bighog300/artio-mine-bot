"""add embeddings columns to records

Revision ID: a12f9e3d4c5b
Revises: 7a1d2f4b8c9e
Create Date: 2026-04-15 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a12f9e3d4c5b"
down_revision: Union[str, Sequence[str], None] = "7a1d2f4b8c9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("embedding_vector", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_records_embedding_updated_at", ["embedding_updated_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.drop_index("ix_records_embedding_updated_at")
        batch_op.drop_column("embedding_updated_at")
        batch_op.drop_column("embedding_vector")
