"""add backfill schedules and policies

Revision ID: b2f7e91c4d11
Revises: a1b2c3d4e5f6
Create Date: 2026-04-16 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f7e91c4d11"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backfill_schedules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("schedule_type", sa.String(), nullable=False, server_default="recurring"),
        sa.Column("cron_expression", sa.String(), nullable=True),
        sa.Column("filters_json", sa.Text(), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("auto_start", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backfill_schedules_tenant_id", "backfill_schedules", ["tenant_id"], unique=False)
    op.create_index("ix_backfill_schedules_enabled", "backfill_schedules", ["enabled"], unique=False)
    op.create_index("ix_backfill_schedules_next_run_at", "backfill_schedules", ["next_run_at"], unique=False)

    op.create_table(
        "backfill_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=False),
        sa.Column("action_json", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backfill_policies_tenant_id", "backfill_policies", ["tenant_id"], unique=False)
    op.create_index("ix_backfill_policies_enabled", "backfill_policies", ["enabled"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_backfill_policies_enabled", table_name="backfill_policies", if_exists=True)
    op.drop_index("ix_backfill_policies_tenant_id", table_name="backfill_policies", if_exists=True)
    op.drop_table("backfill_policies", if_exists=True)

    op.drop_index("ix_backfill_schedules_next_run_at", table_name="backfill_schedules", if_exists=True)
    op.drop_index("ix_backfill_schedules_enabled", table_name="backfill_schedules", if_exists=True)
    op.drop_index("ix_backfill_schedules_tenant_id", table_name="backfill_schedules", if_exists=True)
    op.drop_table("backfill_schedules", if_exists=True)
