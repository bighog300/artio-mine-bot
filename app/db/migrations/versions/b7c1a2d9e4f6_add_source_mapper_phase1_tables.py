"""add source mapper phase1 tables

Revision ID: b7c1a2d9e4f6
Revises: 1f6b2a9c8d7e
Create Date: 2026-04-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c1a2d9e4f6"
down_revision: Union[str, Sequence[str], None] = "1f6b2a9c8d7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_DATETIME = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "source_mapping_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="public"),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("scan_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("scan_options_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("published_by", sa.String(), nullable=True),
        sa.Column("published_at", UTC_DATETIME, nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "version_number", name="uq_source_mapping_versions_source_version"),
    )
    op.create_index("ix_source_mapping_versions_source_id", "source_mapping_versions", ["source_id"])
    op.create_index("ix_source_mapping_versions_source_status", "source_mapping_versions", ["source_id", "status"])

    op.add_column("sources", sa.Column("active_mapping_version_id", sa.String(), nullable=True))
    op.add_column("sources", sa.Column("mapping_status", sa.String(), nullable=False, server_default="none"))
    op.add_column("sources", sa.Column("last_mapping_scan_at", UTC_DATETIME, nullable=True))
    op.add_column("sources", sa.Column("last_mapping_error", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_sources_active_mapping_version_id",
        "sources",
        "source_mapping_versions",
        ["active_mapping_version_id"],
        ["id"],
    )

    op.create_table(
        "source_mapping_page_types",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("classifier_signals_json", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mapping_version_id", "key", name="uq_source_mapping_page_types_version_key"),
    )
    op.create_index("ix_source_mapping_page_types_version_id", "source_mapping_page_types", ["mapping_version_id"])

    op.create_table(
        "source_mapping_samples",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=True),
        sa.Column("page_type_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("html_snapshot", sa.Text(), nullable=True),
        sa.Column("dom_summary_json", sa.Text(), nullable=True),
        sa.Column("structured_data_json", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"]),
        sa.ForeignKeyConstraint(["page_type_id"], ["source_mapping_page_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_mapping_samples_mapping_version_id", "source_mapping_samples", ["mapping_version_id"])
    op.create_index("ix_source_mapping_samples_page_type_id", "source_mapping_samples", ["page_type_id"])

    op.create_table(
        "source_mapping_rows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=False),
        sa.Column("page_type_id", sa.String(), nullable=True),
        sa.Column("selector", sa.String(), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=False, server_default="css"),
        sa.Column("extraction_mode", sa.String(), nullable=False, server_default="text"),
        sa.Column("attribute_name", sa.String(), nullable=True),
        sa.Column("sample_value", sa.Text(), nullable=True),
        sa.Column("destination_entity", sa.String(), nullable=False),
        sa.Column("destination_field", sa.String(), nullable=False),
        sa.Column("category_target", sa.String(), nullable=True),
        sa.Column("transforms_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(), nullable=False, server_default="proposed"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["page_type_id"], ["source_mapping_page_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_mapping_rows_mapping_version_id", "source_mapping_rows", ["mapping_version_id"])
    op.create_index("ix_source_mapping_rows_mapping_version_status", "source_mapping_rows", ["mapping_version_id", "status"])
    op.create_index("ix_source_mapping_rows_mapping_version_destination_entity", "source_mapping_rows", ["mapping_version_id", "destination_entity"])
    op.create_index("ix_source_mapping_rows_page_type_destination", "source_mapping_rows", ["page_type_id", "destination_entity", "destination_field"])

    op.create_table(
        "source_mapping_sample_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("completed_at", UTC_DATETIME, nullable=True),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "source_mapping_sample_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sample_run_id", sa.String(), nullable=False),
        sa.Column("sample_id", sa.String(), nullable=True),
        sa.Column("record_preview_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["source_mapping_samples.id"]),
        sa.ForeignKeyConstraint(["sample_run_id"], ["source_mapping_sample_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("source_mapping_sample_results", if_exists=True)
    op.drop_table("source_mapping_sample_runs", if_exists=True)
    op.drop_index("ix_source_mapping_rows_page_type_destination", table_name="source_mapping_rows", if_exists=True)
    op.drop_index("ix_source_mapping_rows_mapping_version_destination_entity", table_name="source_mapping_rows", if_exists=True)
    op.drop_index("ix_source_mapping_rows_mapping_version_status", table_name="source_mapping_rows", if_exists=True)
    op.drop_index("ix_source_mapping_rows_mapping_version_id", table_name="source_mapping_rows", if_exists=True)
    op.drop_table("source_mapping_rows", if_exists=True)
    op.drop_index("ix_source_mapping_samples_page_type_id", table_name="source_mapping_samples", if_exists=True)
    op.drop_index("ix_source_mapping_samples_mapping_version_id", table_name="source_mapping_samples", if_exists=True)
    op.drop_table("source_mapping_samples", if_exists=True)
    op.drop_index("ix_source_mapping_page_types_version_id", table_name="source_mapping_page_types", if_exists=True)
    op.drop_table("source_mapping_page_types", if_exists=True)
    op.drop_constraint("fk_sources_active_mapping_version_id", "sources", type_="foreignkey", if_exists=True)
    op.drop_column("sources", "last_mapping_error", if_exists=True)
    op.drop_column("sources", "last_mapping_scan_at", if_exists=True)
    op.drop_column("sources", "mapping_status", if_exists=True)
    op.drop_column("sources", "active_mapping_version_id", if_exists=True)
    op.drop_index("ix_source_mapping_versions_source_status", table_name="source_mapping_versions", if_exists=True)
    op.drop_index("ix_source_mapping_versions_source_id", table_name="source_mapping_versions", if_exists=True)
    op.drop_table("source_mapping_versions", if_exists=True)
