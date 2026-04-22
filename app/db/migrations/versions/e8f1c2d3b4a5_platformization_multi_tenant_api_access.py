"""platformization multi-tenant api access

Revision ID: e8f1c2d3b4a5
Revises: d1a2b3c4d5e6
Create Date: 2026-04-15 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f1c2d3b4a5"
down_revision: Union[str, Sequence[str], None] = "d1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=False)

    op.execute(
        sa.text(
            "INSERT INTO tenants (id, name, is_active, created_at, updated_at) "
            "VALUES ('public', 'Public', true, now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )

    op.add_column("sources", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE sources SET tenant_id = 'public' WHERE tenant_id IS NULL"))
    op.alter_column("sources", "tenant_id", nullable=False)
    op.create_foreign_key(None, "sources", "tenants", ["tenant_id"], ["id"])

    op.add_column("pages", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE pages SET tenant_id = 'public' WHERE tenant_id IS NULL"))
    op.alter_column("pages", "tenant_id", nullable=False)

    op.add_column("records", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE records SET tenant_id = 'public' WHERE tenant_id IS NULL"))
    op.alter_column("records", "tenant_id", nullable=False)

    op.add_column("images", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE images SET tenant_id = 'public' WHERE tenant_id IS NULL"))
    op.alter_column("images", "tenant_id", nullable=False)

    op.add_column("jobs", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE jobs SET tenant_id = 'public' WHERE tenant_id IS NULL"))
    op.alter_column("jobs", "tenant_id", nullable=False)

    op.create_index("ix_pages_tenant_id", "pages", ["tenant_id"], unique=False)
    op.create_index("ix_records_tenant_id", "records", ["tenant_id"], unique=False)
    op.create_index("ix_images_tenant_id", "images", ["tenant_id"], unique=False)
    op.create_index("ix_jobs_tenant_id", "jobs", ["tenant_id"], unique=False)

    op.create_foreign_key(None, "pages", "tenants", ["tenant_id"], ["id"])
    op.create_foreign_key(None, "records", "tenants", ["tenant_id"], ["id"])
    op.create_foreign_key(None, "images", "tenants", ["tenant_id"], ["id"])
    op.create_foreign_key(None, "jobs", "tenants", ["tenant_id"], ["id"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("permissions_json", sa.Text(), nullable=False, server_default='["read"]'),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"], unique=False)
    op.create_index("ix_api_keys_enabled", "api_keys", ["enabled"], unique=False)

    op.create_table(
        "api_usage_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("api_key_id", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_usage_events_api_key_id", "api_usage_events", ["api_key_id"], unique=False)
    op.create_index("ix_api_usage_events_tenant_id", "api_usage_events", ["tenant_id"], unique=False)
    op.create_index("ix_api_usage_events_endpoint", "api_usage_events", ["endpoint"], unique=False)
    op.create_index("ix_api_usage_events_created_at", "api_usage_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_usage_events_created_at", table_name="api_usage_events", if_exists=True)
    op.drop_index("ix_api_usage_events_endpoint", table_name="api_usage_events", if_exists=True)
    op.drop_index("ix_api_usage_events_tenant_id", table_name="api_usage_events", if_exists=True)
    op.drop_index("ix_api_usage_events_api_key_id", table_name="api_usage_events", if_exists=True)
    op.drop_table("api_usage_events", if_exists=True)

    op.drop_index("ix_api_keys_enabled", table_name="api_keys", if_exists=True)
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys", if_exists=True)
    op.drop_table("api_keys", if_exists=True)

    op.drop_index("ix_jobs_tenant_id", table_name="jobs", if_exists=True)
    op.drop_index("ix_images_tenant_id", table_name="images", if_exists=True)
    op.drop_index("ix_records_tenant_id", table_name="records", if_exists=True)
    op.drop_index("ix_pages_tenant_id", table_name="pages", if_exists=True)

    op.drop_column("jobs", "tenant_id", if_exists=True)
    op.drop_column("images", "tenant_id", if_exists=True)
    op.drop_column("records", "tenant_id", if_exists=True)
    op.drop_column("pages", "tenant_id", if_exists=True)
    op.drop_column("sources", "tenant_id", if_exists=True)

    op.drop_index("ix_tenants_name", table_name="tenants", if_exists=True)
    op.drop_table("tenants", if_exists=True)
