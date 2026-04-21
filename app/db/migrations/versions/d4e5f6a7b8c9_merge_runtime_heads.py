"""merge runtime heads

Revision ID: d4e5f6a7b8c9
Revises: 5f2a9b7c3d1e, 7c9e1a2b3d4f, 9a7b6c5d4e3f
Create Date: 2026-04-21 00:00:00.000000
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = (
    "5f2a9b7c3d1e",
    "7c9e1a2b3d4f",
    "9a7b6c5d4e3f",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
