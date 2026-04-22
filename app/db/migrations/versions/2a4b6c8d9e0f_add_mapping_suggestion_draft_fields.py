"""add mapping suggestion draft fields

Revision ID: 2a4b6c8d9e0f
Revises: 1c2d3e4f5a6b
Create Date: 2026-04-21 01:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a4b6c8d9e0f"
down_revision: Union[str, Sequence[str], None] = "1c2d3e4f5a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("source_mapping_versions", sa.Column("based_on_profile_id", sa.String(), nullable=True))
    op.add_column("source_mapping_versions", sa.Column("mapping_json", sa.Text(), nullable=False, server_default="{}"))
    op.create_foreign_key(
        "fk_source_mapping_versions_based_on_profile_id",
        "source_mapping_versions",
        "source_profiles",
        ["based_on_profile_id"],
        ["id"],
    )
    op.alter_column("source_mapping_versions", "mapping_json", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_source_mapping_versions_based_on_profile_id", "source_mapping_versions", type_="foreignkey", if_exists=True)
    op.drop_column("source_mapping_versions", "mapping_json", if_exists=True)
    op.drop_column("source_mapping_versions", "based_on_profile_id", if_exists=True)
