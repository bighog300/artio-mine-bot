"""add backfill tables

Revision ID: a1b2c3d4e5f6
Revises: f4b2c7d9e1aa
Create Date: 2026-04-16 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4b2c7d9e1aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("records", sa.Column("completeness_details", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE records SET completeness_details = '{}' WHERE completeness_details IS NULL"))
    op.alter_column("records", "completeness_details", nullable=False, server_default=sa.text("'{}'"))

    op.create_table(
        "backfill_campaigns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("filters_json", sa.Text(), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_updates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_updates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backfill_campaigns_tenant_id", "backfill_campaigns", ["tenant_id"], unique=False)
    op.create_index("ix_backfill_campaigns_status", "backfill_campaigns", ["status"], unique=False)
    op.create_index("ix_backfill_campaigns_created_at", "backfill_campaigns", ["created_at"], unique=False)

    op.create_table(
        "backfill_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("url_to_crawl", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("before_completeness", sa.Integer(), nullable=True),
        sa.Column("after_completeness", sa.Integer(), nullable=True),
        sa.Column("fields_updated", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["backfill_campaigns.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backfill_jobs_tenant_id", "backfill_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_backfill_jobs_campaign_id", "backfill_jobs", ["campaign_id"], unique=False)
    op.create_index("ix_backfill_jobs_record_id", "backfill_jobs", ["record_id"], unique=False)
    op.create_index("ix_backfill_jobs_status", "backfill_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_backfill_jobs_status", table_name="backfill_jobs")
    op.drop_index("ix_backfill_jobs_record_id", table_name="backfill_jobs")
    op.drop_index("ix_backfill_jobs_campaign_id", table_name="backfill_jobs")
    op.drop_index("ix_backfill_jobs_tenant_id", table_name="backfill_jobs")
    op.drop_table("backfill_jobs")

    op.drop_index("ix_backfill_campaigns_created_at", table_name="backfill_campaigns")
    op.drop_index("ix_backfill_campaigns_status", table_name="backfill_campaigns")
    op.drop_index("ix_backfill_campaigns_tenant_id", table_name="backfill_campaigns")
    op.drop_table("backfill_campaigns")

    op.drop_column("records", "completeness_details")
