"""add durable crawl state tables and crawl_run links

Revision ID: 11c9f5a2d2aa
Revises: c1e9d4a7b8f0
Create Date: 2026-04-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "11c9f5a2d2aa"
down_revision: Union[str, Sequence[str], None] = "c1e9d4a7b8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="public"),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("seed_url", sa.String(), nullable=False),
        sa.Column("worker_id", sa.String(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_runs_source_id_status", "crawl_runs", ["source_id", "status"], unique=False)
    op.create_index("ix_crawl_runs_last_heartbeat_at", "crawl_runs", ["last_heartbeat_at"], unique=False)

    op.create_table(
        "crawl_frontier",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="public"),
        sa.Column("crawl_run_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("normalized_url", sa.String(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discovered_from_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("leased_by_worker", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "normalized_url", name="uq_crawl_frontier_source_normalized_url"),
    )
    op.create_index("ix_crawl_frontier_crawl_run_id_status", "crawl_frontier", ["crawl_run_id", "status"], unique=False)
    op.create_index("ix_crawl_frontier_lease_expires_at", "crawl_frontier", ["lease_expires_at"], unique=False)
    op.create_index("ix_crawl_frontier_next_retry_at", "crawl_frontier", ["next_retry_at"], unique=False)

    op.add_column("jobs", sa.Column("crawl_run_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_jobs_crawl_run_id", "jobs", "crawl_runs", ["crawl_run_id"], ["id"])
    op.create_index("ix_jobs_crawl_run_id", "jobs", ["crawl_run_id"], unique=False)

    op.add_column("pages", sa.Column("crawl_run_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_pages_crawl_run_id", "pages", "crawl_runs", ["crawl_run_id"], ["id"])
    op.create_index("ix_pages_crawl_run_id", "pages", ["crawl_run_id"], unique=False)

    op.add_column("records", sa.Column("crawl_run_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_records_crawl_run_id", "records", "crawl_runs", ["crawl_run_id"], ["id"])
    op.create_index("ix_records_crawl_run_id", "records", ["crawl_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_records_crawl_run_id", table_name="records", if_exists=True)
    op.drop_constraint("fk_records_crawl_run_id", "records", type_="foreignkey", if_exists=True)
    op.drop_column("records", "crawl_run_id", if_exists=True)

    op.drop_index("ix_pages_crawl_run_id", table_name="pages", if_exists=True)
    op.drop_constraint("fk_pages_crawl_run_id", "pages", type_="foreignkey", if_exists=True)
    op.drop_column("pages", "crawl_run_id", if_exists=True)

    op.drop_index("ix_jobs_crawl_run_id", table_name="jobs", if_exists=True)
    op.drop_constraint("fk_jobs_crawl_run_id", "jobs", type_="foreignkey", if_exists=True)
    op.drop_column("jobs", "crawl_run_id", if_exists=True)

    op.drop_index("ix_crawl_frontier_next_retry_at", table_name="crawl_frontier", if_exists=True)
    op.drop_index("ix_crawl_frontier_lease_expires_at", table_name="crawl_frontier", if_exists=True)
    op.drop_index("ix_crawl_frontier_crawl_run_id_status", table_name="crawl_frontier", if_exists=True)
    op.drop_table("crawl_frontier", if_exists=True)

    op.drop_index("ix_crawl_runs_last_heartbeat_at", table_name="crawl_runs", if_exists=True)
    op.drop_index("ix_crawl_runs_source_id_status", table_name="crawl_runs", if_exists=True)
    op.drop_table("crawl_runs", if_exists=True)
