"""add source profiles and url families

Revision ID: 1c2d3e4f5a6b
Revises: 6f0e2d1c9b7a
Create Date: 2026-04-21 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c2d3e4f5a6b"
down_revision: Union[str, Sequence[str], None] = "6f0e2d1c9b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("seed_url", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("site_fingerprint", sa.Text(), nullable=False),
        sa.Column("sitemap_urls", sa.Text(), nullable=False),
        sa.Column("nav_discovery_summary", sa.Text(), nullable=False),
        sa.Column("profile_metrics_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_profiles_source_id_started_at", "source_profiles", ["source_id", "started_at"])
    op.create_index("ix_source_profiles_source_id_status", "source_profiles", ["source_id", "status"])

    op.create_table(
        "url_families",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_profile_id", sa.String(), nullable=False),
        sa.Column("family_key", sa.String(), nullable=False),
        sa.Column("family_label", sa.String(), nullable=False),
        sa.Column("path_pattern", sa.String(), nullable=False),
        sa.Column("page_type_candidate", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_urls_json", sa.Text(), nullable=False),
        sa.Column("follow_policy_candidate", sa.String(), nullable=True),
        sa.Column("pagination_policy_candidate", sa.String(), nullable=True),
        sa.Column("include_by_default", sa.Boolean(), nullable=False),
        sa.Column("diagnostics_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_profile_id"], ["source_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_profile_id", "family_key", name="uq_url_families_profile_family"),
    )
    op.create_index("ix_url_families_profile_id_confidence", "url_families", ["source_profile_id", "confidence"])


def downgrade() -> None:
    op.drop_index("ix_url_families_profile_id_confidence", table_name="url_families")
    op.drop_table("url_families")
    op.drop_index("ix_source_profiles_source_id_status", table_name="source_profiles")
    op.drop_index("ix_source_profiles_source_id_started_at", table_name="source_profiles")
    op.drop_table("source_profiles")
