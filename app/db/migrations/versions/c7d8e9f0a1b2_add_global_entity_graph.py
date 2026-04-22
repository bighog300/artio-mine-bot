"""add global entity graph

Revision ID: c7d8e9f0a1b2
Revises: bc34de56fa78
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "bc34de56fa78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("canonical_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])
    op.create_index("ix_entities_source_id", "entities", ["source_id"])

    op.create_table(
        "entity_links",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("match_method", sa.String(), nullable=False, server_default="exact"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", name="uq_entity_links_record"),
        sa.UniqueConstraint("entity_id", "record_id", name="uq_entity_links_entity_record"),
    )
    op.create_index("ix_entity_links_entity_id", "entity_links", ["entity_id"])
    op.create_index("ix_entity_links_source_id", "entity_links", ["source_id"])

    with op.batch_alter_table("entity_relationships") as batch_op:
        batch_op.alter_column("from_record_id", existing_type=sa.String(), nullable=True)
        batch_op.alter_column("to_record_id", existing_type=sa.String(), nullable=True)
        batch_op.add_column(sa.Column("from_entity_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("to_entity_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("source_record_id", sa.String(), nullable=True))
        batch_op.create_foreign_key("fk_entity_relationships_from_entity", "entities", ["from_entity_id"], ["id"])
        batch_op.create_foreign_key("fk_entity_relationships_to_entity", "entities", ["to_entity_id"], ["id"])
        batch_op.create_foreign_key("fk_entity_relationships_source_record", "records", ["source_record_id"], ["id"])
        batch_op.create_index("ix_entity_relationships_from_entity_id", ["from_entity_id"])
        batch_op.create_index("ix_entity_relationships_to_entity_id", ["to_entity_id"])
        batch_op.create_unique_constraint(
            "uq_entity_relationships_entity_dedup",
            ["from_entity_id", "to_entity_id", "relationship_type", "source_record_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("entity_relationships") as batch_op:
        batch_op.drop_constraint("uq_entity_relationships_entity_dedup", type_="unique", if_exists=True)
        batch_op.drop_index("ix_entity_relationships_to_entity_id", if_exists=True)
        batch_op.drop_index("ix_entity_relationships_from_entity_id", if_exists=True)
        batch_op.drop_constraint("fk_entity_relationships_source_record", type_="foreignkey", if_exists=True)
        batch_op.drop_constraint("fk_entity_relationships_to_entity", type_="foreignkey", if_exists=True)
        batch_op.drop_constraint("fk_entity_relationships_from_entity", type_="foreignkey", if_exists=True)
        batch_op.drop_column("source_record_id", if_exists=True)
        batch_op.drop_column("confidence_score", if_exists=True)
        batch_op.drop_column("to_entity_id", if_exists=True)
        batch_op.drop_column("from_entity_id", if_exists=True)
        batch_op.alter_column("to_record_id", existing_type=sa.String(), nullable=False)
        batch_op.alter_column("from_record_id", existing_type=sa.String(), nullable=False)

    op.drop_index("ix_entity_links_source_id", table_name="entity_links", if_exists=True)
    op.drop_index("ix_entity_links_entity_id", table_name="entity_links", if_exists=True)
    op.drop_table("entity_links", if_exists=True)

    op.drop_index("ix_entities_source_id", table_name="entities", if_exists=True)
    op.drop_index("ix_entities_canonical_name", table_name="entities", if_exists=True)
    op.drop_index("ix_entities_entity_type", table_name="entities", if_exists=True)
    op.drop_table("entities", if_exists=True)
