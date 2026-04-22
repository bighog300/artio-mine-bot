"""add job runtime visibility fields and job events table

Revision ID: c9d8e7f6a5b4
Revises: b2f7e91c4d11, b7c1a2d9e4f6
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = ("b2f7e91c4d11", "b7c1a2d9e4f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("current_stage", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("current_item", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("last_log_message", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("metrics_json", sa.Text(), nullable=True))

    op.create_table(
        "job_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(), nullable=False, server_default="info"),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_events_job_id_timestamp", "job_events", ["job_id", "timestamp"], unique=False)
    op.create_index("ix_job_events_source_id_timestamp", "job_events", ["source_id", "timestamp"], unique=False)
    op.create_index("ix_job_events_event_type", "job_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_events_event_type", table_name="job_events", if_exists=True)
    op.drop_index("ix_job_events_source_id_timestamp", table_name="job_events", if_exists=True)
    op.drop_index("ix_job_events_job_id_timestamp", table_name="job_events", if_exists=True)
    op.drop_table("job_events", if_exists=True)

    op.drop_column("jobs", "metrics_json", if_exists=True)
    op.drop_column("jobs", "last_log_message", if_exists=True)
    op.drop_column("jobs", "last_heartbeat_at", if_exists=True)
    op.drop_column("jobs", "progress_total", if_exists=True)
    op.drop_column("jobs", "progress_current", if_exists=True)
    op.drop_column("jobs", "current_item", if_exists=True)
    op.drop_column("jobs", "current_stage", if_exists=True)
