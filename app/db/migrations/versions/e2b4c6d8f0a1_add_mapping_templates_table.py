"""add mapping templates table

Revision ID: e2b4c6d8f0a1
Revises: a7c9e2f4b1d3
Create Date: 2026-04-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2b4c6d8f0a1"
down_revision: Union[str, Sequence[str], None] = "a7c9e2f4b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mapping_templates",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_mapping_templates_name"),
    )
    op.create_index("ix_mapping_templates_created_at", "mapping_templates", ["created_at"])
    op.create_index("ix_mapping_templates_is_system", "mapping_templates", ["is_system"])


def downgrade() -> None:
    op.drop_index("ix_mapping_templates_is_system", table_name="mapping_templates")
    op.drop_index("ix_mapping_templates_created_at", table_name="mapping_templates")
    op.drop_table("mapping_templates")
