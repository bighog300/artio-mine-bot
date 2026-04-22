"""add audit events table

Revision ID: aa91c5ef42d1
Revises: 8c4f2e7a1b9d
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aa91c5ef42d1"
down_revision: Union[str, Sequence[str], None] = "8c4f2e7a1b9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UTC_DATETIME = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("user_name", sa.String(), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("record_id", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("changes_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_record_id", "audit_events", ["record_id"])
    op.create_index("ix_audit_events_source_id", "audit_events", ["source_id"])
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_user_id", table_name="audit_events", if_exists=True)
    op.drop_index("ix_audit_events_source_id", table_name="audit_events", if_exists=True)
    op.drop_index("ix_audit_events_record_id", table_name="audit_events", if_exists=True)
    op.drop_index("ix_audit_events_event_type", table_name="audit_events", if_exists=True)
    op.drop_index("ix_audit_events_entity_type", table_name="audit_events", if_exists=True)
    op.drop_index("ix_audit_events_entity_id", table_name="audit_events", if_exists=True)
    op.drop_index("ix_audit_events_created_at", table_name="audit_events", if_exists=True)
    op.drop_table("audit_events", if_exists=True)
