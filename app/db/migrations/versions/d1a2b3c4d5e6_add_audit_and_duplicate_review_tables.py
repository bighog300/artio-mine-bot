"""add audit and duplicate review tables

Revision ID: d1a2b3c4d5e6
Revises: a12f9e3d4c5b
Create Date: 2026-04-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1a2b3c4d5e6"
down_revision = "a12f9e3d4c5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "duplicate_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("left_record_id", sa.String(), nullable=False),
        sa.Column("right_record_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("similarity_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merge_target_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["left_record_id"], ["records.id"]),
        sa.ForeignKeyConstraint(["right_record_id"], ["records.id"]),
        sa.ForeignKeyConstraint(["merge_target_id"], ["records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("left_record_id", "right_record_id", name="uq_duplicate_reviews_pair"),
    )
    op.create_index("ix_duplicate_reviews_status", "duplicate_reviews", ["status"])
    op.create_index("ix_duplicate_reviews_similarity_score", "duplicate_reviews", ["similarity_score"])

    op.create_table(
        "audit_actions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("record_id", sa.String(), nullable=True),
        sa.Column("affected_record_ids", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_actions_action_type", "audit_actions", ["action_type"])
    op.create_index("ix_audit_actions_created_at", "audit_actions", ["created_at"])
    op.create_index("ix_audit_actions_record_id", "audit_actions", ["record_id"])
    op.create_index("ix_audit_actions_source_id", "audit_actions", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_actions_source_id", table_name="audit_actions")
    op.drop_index("ix_audit_actions_record_id", table_name="audit_actions")
    op.drop_index("ix_audit_actions_created_at", table_name="audit_actions")
    op.drop_index("ix_audit_actions_action_type", table_name="audit_actions")
    op.drop_table("audit_actions")

    op.drop_index("ix_duplicate_reviews_similarity_score", table_name="duplicate_reviews")
    op.drop_index("ix_duplicate_reviews_status", table_name="duplicate_reviews")
    op.drop_table("duplicate_reviews")
