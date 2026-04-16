"""add worker runtime controls and worker states

Revision ID: f1a2b3c4d5e7
Revises: c9d8e7f6a5b4
Create Date: 2026-04-16 00:00:01.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("worker_id", sa.String(), nullable=True))
    op.create_index("ix_jobs_worker_id", "jobs", ["worker_id"], unique=False)

    op.add_column("job_events", sa.Column("worker_id", sa.String(), nullable=True))
    op.create_index("ix_job_events_worker_id_timestamp", "job_events", ["worker_id", "timestamp"], unique=False)

    op.create_table(
        "worker_states",
        sa.Column("worker_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="idle"),
        sa.Column("current_job_id", sa.String(), nullable=True),
        sa.Column("current_stage", sa.String(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["current_job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("worker_id"),
    )
    op.create_index("ix_worker_states_status", "worker_states", ["status"], unique=False)
    op.create_index("ix_worker_states_last_heartbeat_at", "worker_states", ["last_heartbeat_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_worker_states_last_heartbeat_at", table_name="worker_states")
    op.drop_index("ix_worker_states_status", table_name="worker_states")
    op.drop_table("worker_states")

    op.drop_index("ix_job_events_worker_id_timestamp", table_name="job_events")
    op.drop_column("job_events", "worker_id")

    op.drop_index("ix_jobs_worker_id", table_name="jobs")
    op.drop_column("jobs", "worker_id")
