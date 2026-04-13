"""add logs table

Revision ID: 9f3c2b1a7e4d
Revises: 5e2c81fd2cc6
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f3c2b1a7e4d"
down_revision: Union[str, Sequence[str], None] = "5e2c81fd2cc6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.create_index("ix_logs_timestamp", ["timestamp"], unique=False)
        batch_op.create_index("ix_logs_level", ["level"], unique=False)
        batch_op.create_index("ix_logs_service", ["service"], unique=False)
        batch_op.create_index("ix_logs_source_id", ["source_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_index("ix_logs_source_id")
        batch_op.drop_index("ix_logs_service")
        batch_op.drop_index("ix_logs_level")
        batch_op.drop_index("ix_logs_timestamp")

    op.drop_table("logs")
