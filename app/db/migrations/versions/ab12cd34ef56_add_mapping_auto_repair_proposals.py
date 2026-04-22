"""add mapping auto repair proposals

Revision ID: ab12cd34ef56
Revises: c6b1d2e3f4a5, e2b4c6d8f0a1
Create Date: 2026-04-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab12cd34ef56"
down_revision: str | Sequence[str] | None = ("c6b1d2e3f4a5", "e2b4c6d8f0a1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("mapping_drift_signals", sa.Column("mapping_field", sa.String(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("selector_path", sa.String(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("failing_selector", sa.String(), nullable=True))

    op.create_table(
        "mapping_repair_proposals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=True),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("old_selector", sa.String(), nullable=True),
        sa.Column("proposed_selector", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("supporting_pages_json", sa.Text(), nullable=False),
        sa.Column("drift_signals_used_json", sa.Text(), nullable=False),
        sa.Column("validation_results_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_mapping_version_id", sa.String(), nullable=True),
        sa.Column("feedback_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["applied_mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mapping_repair_proposals_source_status",
        "mapping_repair_proposals",
        ["source_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_mapping_repair_proposals_mapping_field",
        "mapping_repair_proposals",
        ["mapping_version_id", "field_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mapping_repair_proposals_mapping_field", table_name="mapping_repair_proposals", if_exists=True)
    op.drop_index("ix_mapping_repair_proposals_source_status", table_name="mapping_repair_proposals", if_exists=True)
    op.drop_table("mapping_repair_proposals", if_exists=True)
    op.drop_column("mapping_drift_signals", "failing_selector", if_exists=True)
    op.drop_column("mapping_drift_signals", "selector_path", if_exists=True)
    op.drop_column("mapping_drift_signals", "mapping_field", if_exists=True)
