"""add extraction drift baselines and field-level signal columns

Revision ID: c6b1d2e3f4a5
Revises: 4f6a9b1c2d3e, 1a2b3c4d5e6f
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c6b1d2e3f4a5"
down_revision = ("4f6a9b1c2d3e", "1a2b3c4d5e6f")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mapping_drift_signals", sa.Column("page_id", sa.String(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("record_id", sa.String(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("field_name", sa.String(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("drift_type", sa.String(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("previous_value", sa.Text(), nullable=True))
    op.add_column("mapping_drift_signals", sa.Column("current_value", sa.Text(), nullable=True))
    op.create_foreign_key(None, "mapping_drift_signals", "pages", ["page_id"], ["id"])
    op.create_foreign_key(None, "mapping_drift_signals", "records", ["record_id"], ["id"])
    op.create_index(
        "ix_mapping_drift_signals_source_page_field",
        "mapping_drift_signals",
        ["source_id", "page_id", "field_name"],
    )

    op.create_table(
        "extraction_baselines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=True),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=True),
        sa.Column("baseline_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("field_stats_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("dom_section_hash", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "page_id", name="uq_extraction_baselines_source_page"),
    )
    op.create_index("ix_extraction_baselines_source_mapping", "extraction_baselines", ["source_id", "mapping_version_id"])
    op.create_index("ix_extraction_baselines_source_updated", "extraction_baselines", ["source_id", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_extraction_baselines_source_updated", table_name="extraction_baselines", if_exists=True)
    op.drop_index("ix_extraction_baselines_source_mapping", table_name="extraction_baselines", if_exists=True)
    op.drop_table("extraction_baselines", if_exists=True)

    op.drop_index("ix_mapping_drift_signals_source_page_field", table_name="mapping_drift_signals", if_exists=True)
    op.drop_constraint(None, "mapping_drift_signals", type_="foreignkey", if_exists=True)
    op.drop_constraint(None, "mapping_drift_signals", type_="foreignkey", if_exists=True)
    op.drop_column("mapping_drift_signals", "current_value", if_exists=True)
    op.drop_column("mapping_drift_signals", "previous_value", if_exists=True)
    op.drop_column("mapping_drift_signals", "confidence", if_exists=True)
    op.drop_column("mapping_drift_signals", "drift_type", if_exists=True)
    op.drop_column("mapping_drift_signals", "field_name", if_exists=True)
    op.drop_column("mapping_drift_signals", "record_id", if_exists=True)
    op.drop_column("mapping_drift_signals", "page_id", if_exists=True)
