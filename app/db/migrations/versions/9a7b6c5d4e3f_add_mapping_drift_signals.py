"""add mapping drift signal persistence

Revision ID: 9a7b6c5d4e3f
Revises: 6f0e2d1c9b7a
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9a7b6c5d4e3f"
down_revision = "6f0e2d1c9b7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mapping_drift_signals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="public"),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=True),
        sa.Column("family_key", sa.String(), nullable=True),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="medium"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("diagnostics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sample_urls_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("proposed_action", sa.String(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mapping_drift_signals_source_status_detected",
        "mapping_drift_signals",
        ["source_id", "status", "detected_at"],
    )
    op.create_index(
        "ix_mapping_drift_signals_mapping_severity_status",
        "mapping_drift_signals",
        ["mapping_version_id", "severity", "status"],
    )
    op.create_index(
        "ix_mapping_drift_signals_source_type_family",
        "mapping_drift_signals",
        ["source_id", "signal_type", "family_key"],
    )

    op.alter_column("mapping_drift_signals", "tenant_id", server_default=None)
    op.alter_column("mapping_drift_signals", "severity", server_default=None)
    op.alter_column("mapping_drift_signals", "status", server_default=None)
    op.alter_column("mapping_drift_signals", "metrics_json", server_default=None)
    op.alter_column("mapping_drift_signals", "diagnostics_json", server_default=None)
    op.alter_column("mapping_drift_signals", "sample_urls_json", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_mapping_drift_signals_source_type_family", table_name="mapping_drift_signals")
    op.drop_index("ix_mapping_drift_signals_mapping_severity_status", table_name="mapping_drift_signals")
    op.drop_index("ix_mapping_drift_signals_source_status_detected", table_name="mapping_drift_signals")
    op.drop_table("mapping_drift_signals")
