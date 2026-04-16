"""merge heads 3e7b1a9d2f0c and aa91c5ef42d1

Revision ID: c1e9d4a7b8f0
Revises: 3e7b1a9d2f0c, aa91c5ef42d1
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "c1e9d4a7b8f0"
down_revision: Union[str, Sequence[str], None] = ("3e7b1a9d2f0c", "aa91c5ef42d1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
