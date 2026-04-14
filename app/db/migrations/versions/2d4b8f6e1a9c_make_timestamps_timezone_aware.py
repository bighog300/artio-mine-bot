"""make timestamps timezone aware

Revision ID: 2d4b8f6e1a9c
Revises: 9f3c2b1a7e4d
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d4b8f6e1a9c"
down_revision: Union[str, Sequence[str], None] = "9f3c2b1a7e4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIMESTAMP_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sources", "created_at"),
    ("sources", "updated_at"),
    ("sources", "last_crawled_at"),
    ("pages", "crawled_at"),
    ("pages", "extracted_at"),
    ("pages", "created_at"),
    ("records", "exported_at"),
    ("records", "created_at"),
    ("records", "updated_at"),
    ("images", "created_at"),
    ("jobs", "started_at"),
    ("jobs", "completed_at"),
    ("jobs", "created_at"),
)


def _upgrade_postgresql() -> None:
    for table_name, column_name in TIMESTAMP_COLUMNS:
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )


def _downgrade_postgresql() -> None:
    for table_name, column_name in TIMESTAMP_COLUMNS:
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )


def _upgrade_non_postgresql() -> None:
    for table_name, column_name in TIMESTAMP_COLUMNS:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=sa.DateTime(),
                type_=sa.DateTime(timezone=True),
            )


def _downgrade_non_postgresql() -> None:
    for table_name, column_name in TIMESTAMP_COLUMNS:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(),
            )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _upgrade_postgresql()
        return

    _upgrade_non_postgresql()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _downgrade_postgresql()
        return

    _downgrade_non_postgresql()
