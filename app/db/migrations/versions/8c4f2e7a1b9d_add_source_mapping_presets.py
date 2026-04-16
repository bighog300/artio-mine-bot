"""add source mapping presets tables

Revision ID: 8c4f2e7a1b9d
Revises: f1a2b3c4d5e7
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c4f2e7a1b9d"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UTC_DATETIME = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "source_mapping_presets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="public"),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_from_mapping_version_id", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_type_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["created_from_mapping_version_id"], ["source_mapping_versions.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "name", name="uq_source_mapping_presets_source_name"),
    )
    op.create_index(
        "ix_source_mapping_presets_source_id_created_at",
        "source_mapping_presets",
        ["source_id", "created_at"],
    )

    op.create_table(
        "source_mapping_preset_rows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("preset_id", sa.String(), nullable=False),
        sa.Column("page_type_key", sa.String(), nullable=True),
        sa.Column("page_type_label", sa.String(), nullable=True),
        sa.Column("selector", sa.String(), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=True),
        sa.Column("extraction_mode", sa.String(), nullable=True),
        sa.Column("attribute_name", sa.String(), nullable=True),
        sa.Column("destination_entity", sa.String(), nullable=True),
        sa.Column("destination_field", sa.String(), nullable=True),
        sa.Column("category_target", sa.String(), nullable=True),
        sa.Column("transforms_json", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rationale_json", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(["preset_id"], ["source_mapping_presets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_mapping_preset_rows_preset_id_sort_order",
        "source_mapping_preset_rows",
        ["preset_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_mapping_preset_rows_preset_id_sort_order", table_name="source_mapping_preset_rows")
    op.drop_table("source_mapping_preset_rows")
    op.drop_index("ix_source_mapping_presets_source_id_created_at", table_name="source_mapping_presets")
    op.drop_table("source_mapping_presets")
