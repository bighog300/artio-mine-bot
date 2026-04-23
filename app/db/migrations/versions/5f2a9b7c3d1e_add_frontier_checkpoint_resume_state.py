"""add frontier mapping attribution and crawl run checkpoints

Revision ID: 5f2a9b7c3d1e
Revises: 3b7d9a2c1e6f
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5f2a9b7c3d1e"
down_revision: Union[str, Sequence[str], None] = "3b7d9a2c1e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        constraint.get("name") == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def upgrade() -> None:
    op.add_column("crawl_runs", sa.Column("mapping_version_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_crawl_runs_mapping_version_id",
        "crawl_runs",
        "source_mapping_versions",
        ["mapping_version_id"],
        ["id"],
    )

    op.add_column("crawl_frontier", sa.Column("mapping_version_id", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("canonical_url", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("family_key", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("skip_reason", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("next_eligible_fetch_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crawl_frontier", sa.Column("etag", sa.String(), nullable=True))
    op.add_column("crawl_frontier", sa.Column("last_modified", sa.String(), nullable=True))
    op.add_column(
        "crawl_frontier",
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.add_column("crawl_frontier", sa.Column("last_extracted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crawl_frontier", sa.Column("diagnostics_json", sa.Text(), nullable=False, server_default="{}"))
    op.create_foreign_key(
        "fk_crawl_frontier_mapping_version_id",
        "crawl_frontier",
        "source_mapping_versions",
        ["mapping_version_id"],
        ["id"],
    )

    with op.batch_alter_table("crawl_frontier") as batch_op:
        if _has_unique_constraint("crawl_frontier", "uq_crawl_frontier_source_normalized_url"):
            batch_op.drop_constraint("uq_crawl_frontier_source_normalized_url", type_="unique")
        batch_op.create_unique_constraint(
            "uq_crawl_frontier_source_mapping_normalized_url",
            ["source_id", "mapping_version_id", "normalized_url"],
        )

    op.create_table(
        "crawl_run_checkpoints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="public"),
        sa.Column("crawl_run_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("mapping_version_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("last_checkpoint_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("frontier_counts_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("progress_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("last_processed_url", sa.String(), nullable=True),
        sa.Column("worker_state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["mapping_version_id"], ["source_mapping_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crawl_run_id", name="uq_crawl_run_checkpoints_crawl_run_id"),
    )
    op.create_index("ix_crawl_run_checkpoints_crawl_run_id", "crawl_run_checkpoints", ["crawl_run_id"], unique=False)
    op.create_index("ix_crawl_run_checkpoints_status", "crawl_run_checkpoints", ["status"], unique=False)
    op.create_index("ix_crawl_run_checkpoints_last_checkpoint_at", "crawl_run_checkpoints", ["last_checkpoint_at"], unique=False)

    op.create_index(
        "ix_crawl_frontier_source_mapping_next_eligible",
        "crawl_frontier",
        ["source_id", "mapping_version_id", "next_eligible_fetch_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_frontier_source_mapping_next_eligible", table_name="crawl_frontier", if_exists=True)
    op.drop_index("ix_crawl_run_checkpoints_last_checkpoint_at", table_name="crawl_run_checkpoints", if_exists=True)
    op.drop_index("ix_crawl_run_checkpoints_status", table_name="crawl_run_checkpoints", if_exists=True)
    op.drop_index("ix_crawl_run_checkpoints_crawl_run_id", table_name="crawl_run_checkpoints", if_exists=True)
    op.drop_table("crawl_run_checkpoints", if_exists=True)

    with op.batch_alter_table("crawl_frontier") as batch_op:
        if _has_unique_constraint("crawl_frontier", "uq_crawl_frontier_source_mapping_normalized_url"):
            batch_op.drop_constraint("uq_crawl_frontier_source_mapping_normalized_url", type_="unique")
        batch_op.create_unique_constraint("uq_crawl_frontier_source_normalized_url", ["source_id", "normalized_url"])

    op.drop_constraint("fk_crawl_frontier_mapping_version_id", "crawl_frontier", type_="foreignkey", if_exists=True)
    op.drop_column("crawl_frontier", "diagnostics_json", if_exists=True)
    op.drop_column("crawl_frontier", "last_extracted_at", if_exists=True)
    op.drop_column("crawl_frontier", "first_discovered_at", if_exists=True)
    op.drop_column("crawl_frontier", "last_modified", if_exists=True)
    op.drop_column("crawl_frontier", "etag", if_exists=True)
    op.drop_column("crawl_frontier", "next_eligible_fetch_at", if_exists=True)
    op.drop_column("crawl_frontier", "skip_reason", if_exists=True)
    op.drop_column("crawl_frontier", "family_key", if_exists=True)
    op.drop_column("crawl_frontier", "canonical_url", if_exists=True)
    op.drop_column("crawl_frontier", "mapping_version_id", if_exists=True)

    op.drop_constraint("fk_crawl_runs_mapping_version_id", "crawl_runs", type_="foreignkey", if_exists=True)
    op.drop_column("crawl_runs", "mapping_version_id", if_exists=True)
