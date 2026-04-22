"""entity graph reconciliation hardening

Revision ID: f9c2e4a1b7d0
Revises: c7d8e9f0a1b2
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9c2e4a1b7d0"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("entities") as batch_op:
        batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("merged_into_entity_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_entities_merged_into_entity", "entities", ["merged_into_entity_id"], ["id"])
        batch_op.create_index("ix_entities_is_deleted", ["is_deleted"], unique=False)
        batch_op.create_index("ix_entities_merged_into_entity_id", ["merged_into_entity_id"], unique=False)

    op.execute(
        """
        DELETE FROM entity_relationships
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM entity_relationships
            GROUP BY from_entity_id, to_entity_id, relationship_type
        )
        """
    )

    with op.batch_alter_table("entity_relationships") as batch_op:
        batch_op.drop_constraint("uq_entity_relationships_entity_dedup", type_="unique", if_exists=True)
        batch_op.create_unique_constraint(
            "uq_entity_relationships_entity_unique",
            ["from_entity_id", "to_entity_id", "relationship_type"],
        )


def downgrade() -> None:
    with op.batch_alter_table("entity_relationships") as batch_op:
        batch_op.drop_constraint("uq_entity_relationships_entity_unique", type_="unique", if_exists=True)
        batch_op.create_unique_constraint(
            "uq_entity_relationships_entity_dedup",
            ["from_entity_id", "to_entity_id", "relationship_type", "source_record_id"],
        )

    with op.batch_alter_table("entities") as batch_op:
        batch_op.drop_index("ix_entities_merged_into_entity_id", if_exists=True)
        batch_op.drop_index("ix_entities_is_deleted", if_exists=True)
        batch_op.drop_constraint("fk_entities_merged_into_entity", type_="foreignkey", if_exists=True)
        batch_op.drop_column("deleted_at", if_exists=True)
        batch_op.drop_column("merged_into_entity_id", if_exists=True)
        batch_op.drop_column("is_deleted", if_exists=True)
