"""harden mapping auto repair lifecycle

Revision ID: bc34de56fa78
Revises: ab12cd34ef56
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bc34de56fa78"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mapping_repair_proposals", sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("mapping_repair_proposals", sa.Column("priority_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("mapping_repair_proposals", sa.Column("strategy_used", sa.String(), nullable=True))
    op.add_column("mapping_repair_proposals", sa.Column("reasoning", sa.Text(), nullable=True))
    op.add_column("mapping_repair_proposals", sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("mapping_repair_proposals", "evidence_json", if_exists=True)
    op.drop_column("mapping_repair_proposals", "reasoning", if_exists=True)
    op.drop_column("mapping_repair_proposals", "strategy_used", if_exists=True)
    op.drop_column("mapping_repair_proposals", "priority_score", if_exists=True)
    op.drop_column("mapping_repair_proposals", "occurrence_count", if_exists=True)
