"""add source runtime preset fields

Revision ID: 3e7b1a9d2f0c
Revises: f1a2b3c4d5e7
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3e7b1a9d2f0c"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("active_mapping_preset_id", sa.String(), nullable=True))
    op.add_column("sources", sa.Column("runtime_mapping_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_sources_active_mapping_preset_id",
        "sources",
        "source_mapping_presets",
        ["active_mapping_preset_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_sources_active_mapping_preset_id", "sources", type_="foreignkey")
    op.drop_column("sources", "runtime_mapping_updated_at")
    op.drop_column("sources", "active_mapping_preset_id")
