"""add runtime zero-ai lifecycle fields

Revision ID: 6f0e2d1c9b7a
Revises: 4d2e1c9b8a7f
Create Date: 2026-04-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "6f0e2d1c9b7a"
down_revision = "4d2e1c9b8a7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("published_mapping_version_id", sa.String(), nullable=True))
    op.add_column("sources", sa.Column("runtime_mode", sa.String(), nullable=False, server_default="draft_only"))
    op.add_column("sources", sa.Column("runtime_ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")))
    op.add_column("sources", sa.Column("mapping_stale", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))
    op.add_column("sources", sa.Column("last_discovery_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("last_mapping_published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_sources_published_mapping_version_id",
        "sources",
        "source_mapping_versions",
        ["published_mapping_version_id"],
        ["id"],
    )

    op.add_column("pages", sa.Column("content_hash", sa.String(), nullable=True))
    op.add_column("pages", sa.Column("template_hash", sa.String(), nullable=True))
    op.add_column("pages", sa.Column("classification_method", sa.String(), nullable=True))
    op.add_column("pages", sa.Column("extraction_method", sa.String(), nullable=True))
    op.add_column("pages", sa.Column("review_reason", sa.String(), nullable=True))
    op.add_column("pages", sa.Column("review_status", sa.String(), nullable=True))
    op.add_column("pages", sa.Column("mapping_version_id_used", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_pages_mapping_version_id_used",
        "pages",
        "source_mapping_versions",
        ["mapping_version_id_used"],
        ["id"],
    )

    op.alter_column("sources", "runtime_mode", server_default=None)
    op.alter_column("sources", "runtime_ai_enabled", server_default=None)
    op.alter_column("sources", "mapping_stale", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_pages_mapping_version_id_used", "pages", type_="foreignkey", if_exists=True)
    op.drop_column("pages", "mapping_version_id_used", if_exists=True)
    op.drop_column("pages", "review_status", if_exists=True)
    op.drop_column("pages", "review_reason", if_exists=True)
    op.drop_column("pages", "extraction_method", if_exists=True)
    op.drop_column("pages", "classification_method", if_exists=True)
    op.drop_column("pages", "template_hash", if_exists=True)
    op.drop_column("pages", "content_hash", if_exists=True)

    op.drop_constraint("fk_sources_published_mapping_version_id", "sources", type_="foreignkey", if_exists=True)
    op.drop_column("sources", "last_mapping_published_at", if_exists=True)
    op.drop_column("sources", "last_discovery_run_at", if_exists=True)
    op.drop_column("sources", "mapping_stale", if_exists=True)
    op.drop_column("sources", "runtime_ai_enabled", if_exists=True)
    op.drop_column("sources", "runtime_mode", if_exists=True)
    op.drop_column("sources", "published_mapping_version_id", if_exists=True)
