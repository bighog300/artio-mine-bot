"""record deduplication and integrity hardening

Revision ID: 4f6a9b1c2d3e
Revises: e8f1c2d3b4a5
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f6a9b1c2d3e"
down_revision = "e8f1c2d3b4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("normalized_name", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("fingerprint", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("structured_data", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("field_confidence", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.create_index("ix_records_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_records_normalized_name", ["normalized_name"], unique=False)
        batch_op.create_index("ix_records_fingerprint", ["fingerprint"], unique=False)

    op.execute(
        """
        UPDATE records
        SET record_type = CASE
            WHEN lower(record_type) IN ('artist') THEN 'artist'
            WHEN lower(record_type) IN ('artwork', 'artist_article', 'artist_press', 'artist_memory', 'article') THEN 'artwork'
            WHEN lower(record_type) IN ('event') THEN 'event'
            WHEN lower(record_type) IN ('exhibition') THEN 'exhibition'
            WHEN lower(record_type) IN ('venue') THEN 'venue'
            ELSE 'artwork'
        END
        """
    )

    op.execute(
        """
        UPDATE records
        SET normalized_name = lower(trim(replace(replace(replace(coalesce(title, ''), '.', ''), ',', ''), '  ', ' ')))
        WHERE normalized_name = ''
        """
    )

    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_records_job_id_jobs", "jobs", ["job_id"], ["id"])
        batch_op.create_check_constraint(
            "ck_records_record_type_enum",
            "record_type IN ('artist', 'artwork', 'exhibition', 'event', 'venue')",
        )
        batch_op.create_unique_constraint(
            "uq_records_type_normalized_name_source",
            ["record_type", "normalized_name", "source_id"],
        )

    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_hash", sa.String(), nullable=True))
        batch_op.create_index("ix_images_source_hash", ["source_id", "image_hash"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.drop_index("ix_images_source_hash", if_exists=True)
        batch_op.drop_column("image_hash", if_exists=True)

    with op.batch_alter_table("records", schema=None) as batch_op:
        batch_op.drop_constraint("uq_records_type_normalized_name_source", type_="unique", if_exists=True)
        batch_op.drop_constraint("ck_records_record_type_enum", type_="check", if_exists=True)
        batch_op.drop_constraint("fk_records_job_id_jobs", type_="foreignkey", if_exists=True)
        batch_op.drop_index("ix_records_fingerprint", if_exists=True)
        batch_op.drop_index("ix_records_normalized_name", if_exists=True)
        batch_op.drop_index("ix_records_job_id", if_exists=True)
        batch_op.drop_column("field_confidence", if_exists=True)
        batch_op.drop_column("structured_data", if_exists=True)
        batch_op.drop_column("fingerprint", if_exists=True)
        batch_op.drop_column("normalized_name", if_exists=True)
        batch_op.drop_column("job_id", if_exists=True)
