"""harden crawler idempotency and leases

Revision ID: 0f9e8d7c6b5a
Revises: d4e5f6a7b8c9
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0f9e8d7c6b5a"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE crawl_frontier
    DROP CONSTRAINT IF EXISTS uq_crawl_frontier_source_mapping_normalized_url
    """)

    with op.batch_alter_table("crawl_frontier") as batch_op:
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("worker_id", sa.String(), nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_crawl_frontier_source_normalized_url'
            ) THEN
                ALTER TABLE crawl_frontier
                ADD CONSTRAINT uq_crawl_frontier_source_normalized_url
                UNIQUE (source_id, normalized_url);
            END IF;
            END$$;
            """
        )
    else:
        with op.batch_alter_table("crawl_frontier") as batch_op:
            batch_op.create_unique_constraint(
                "uq_crawl_frontier_source_normalized_url",
                ["source_id", "normalized_url"],
            )

    with op.batch_alter_table("pages") as batch_op:
        batch_op.add_column(sa.Column("normalized_url", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("worker_id", sa.String(), nullable=True))

    op.execute("UPDATE pages SET normalized_url = url WHERE normalized_url IS NULL")

    with op.batch_alter_table("pages") as batch_op:
        batch_op.alter_column("normalized_url", existing_type=sa.String(), nullable=False)
        batch_op.create_unique_constraint("uq_pages_source_normalized_url", ["source_id", "normalized_url"])

    op.create_table(
        "domain_rate_limits",
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("domain"),
    )


def downgrade() -> None:
    op.drop_table("domain_rate_limits", if_exists=True)

    with op.batch_alter_table("pages") as batch_op:
        batch_op.drop_constraint("uq_pages_source_normalized_url", type_="unique", if_exists=True)
        batch_op.drop_column("worker_id", if_exists=True)
        batch_op.drop_column("started_at", if_exists=True)
        batch_op.drop_column("normalized_url", if_exists=True)

    with op.batch_alter_table("crawl_frontier") as batch_op:
        batch_op.drop_constraint("uq_crawl_frontier_source_normalized_url", type_="unique", if_exists=True)
        batch_op.create_unique_constraint(
            "uq_crawl_frontier_source_mapping_normalized_url",
            ["source_id", "mapping_version_id", "normalized_url"],
        )
        batch_op.drop_column("worker_id", if_exists=True)
        batch_op.drop_column("started_at", if_exists=True)
