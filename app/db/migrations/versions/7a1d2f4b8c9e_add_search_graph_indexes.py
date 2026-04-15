"""add search and graph indexes

Revision ID: 7a1d2f4b8c9e
Revises: c3a1f0b4d2aa
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a1d2f4b8c9e"
down_revision: Union[str, Sequence[str], None] = "c3a1f0b4d2aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("has_conflicts", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_records_completeness_score", ["completeness_score"], unique=False)
        batch_op.create_index("ix_records_source_record_type", ["source_id", "record_type"], unique=False)

    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("from_record_id", sa.String(), nullable=False),
        sa.Column("to_record_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["from_record_id"], ["records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["to_record_id"], ["records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "from_record_id",
            "to_record_id",
            "relationship_type",
            name="uq_entity_relationships_dedup",
        ),
    )

    with op.batch_alter_table("entity_relationships", schema=None) as batch_op:
        batch_op.create_index("ix_entity_relationships_source_id", ["source_id"], unique=False)
        batch_op.create_index("ix_entity_relationships_from_record_id", ["from_record_id"], unique=False)
        batch_op.create_index("ix_entity_relationships_to_record_id", ["to_record_id"], unique=False)
        batch_op.create_index("ix_entity_relationships_type", ["relationship_type"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("entity_relationships", schema=None) as batch_op:
        batch_op.drop_index("ix_entity_relationships_type")
        batch_op.drop_index("ix_entity_relationships_to_record_id")
        batch_op.drop_index("ix_entity_relationships_from_record_id")
        batch_op.drop_index("ix_entity_relationships_source_id")

    op.drop_table("entity_relationships")

    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.drop_index("ix_records_source_record_type")
        batch_op.drop_index("ix_records_completeness_score")
        batch_op.drop_column("has_conflicts")
        batch_op.drop_column("completeness_score")
