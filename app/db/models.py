import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


UTC_DATETIME = DateTime(timezone=True)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    operational_status: Mapped[str] = mapped_column(String, default="idle", nullable=False)
    crawl_intent: Mapped[str] = mapped_column(String, default="site_root", nullable=False)
    site_map: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure_map: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    structure_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    crawl_hints: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    queue_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    health_status: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)

    pages: Mapped[list["Page"]] = relationship("Page", back_populates="source", cascade="all, delete-orphan")
    records: Mapped[list["Record"]] = relationship("Record", back_populates="source", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="source", cascade="all, delete-orphan")
    logs: Mapped[list["Log"]] = relationship("Log", back_populates="source")
    schedules: Mapped[list["ScheduledJob"]] = relationship(
        "ScheduledJob",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    original_url: Mapped[str] = mapped_column(String, nullable=False)
    page_type: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fetch_method: Mapped[str | None] = mapped_column(String, nullable=True)
    html_truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawled_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="pages")
    records: Mapped[list["Record"]] = relationship("Record", back_populates="page")
    images: Mapped[list["Image"]] = relationship("Image", back_populates="page")

    __table_args__ = (
        UniqueConstraint("source_id", "url"),
        Index("ix_pages_tenant_id", "tenant_id"),
        Index("ix_pages_source_id", "source_id"),
        Index("ix_pages_status", "status"),
        Index("ix_pages_page_type", "page_type"),
    )


class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    page_id: Mapped[str | None] = mapped_column(String, ForeignKey("pages.id"), nullable=True)
    record_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)

    # Core fields
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Event / Exhibition fields
    start_date: Mapped[str | None] = mapped_column(String, nullable=True)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String, nullable=True)
    venue_address: Mapped[str | None] = mapped_column(String, nullable=True)
    artist_names: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ticket_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_free: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    price_text: Mapped[str | None] = mapped_column(String, nullable=True)
    curator: Mapped[str | None] = mapped_column(String, nullable=True)

    # Artist fields
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mediums: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    collections: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Venue fields
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Artwork fields
    medium: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[str | None] = mapped_column(String, nullable=True)

    # Extraction metadata
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_model: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)

    # Confidence
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String, default="LOW", nullable=False)
    confidence_reasons: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_conflicts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Admin fields
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_image_id: Mapped[str | None] = mapped_column(String, ForeignKey("images.id"), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="records")
    page: Mapped["Page | None"] = relationship("Page", back_populates="records")
    images: Mapped[list["Image"]] = relationship(
        "Image",
        back_populates="record",
        foreign_keys="Image.record_id",
        cascade="all, delete-orphan",
    )
    primary_image: Mapped["Image | None"] = relationship(
        "Image",
        foreign_keys=[primary_image_id],
        primaryjoin="Record.primary_image_id == Image.id",
        uselist=False,
        post_update=True,
    )

    __table_args__ = (
        Index("ix_records_tenant_id", "tenant_id"),
        Index("ix_records_source_id", "source_id"),
        Index("ix_records_status", "status"),
        Index("ix_records_record_type", "record_type"),
        Index("ix_records_confidence_band", "confidence_band"),
        Index("ix_records_completeness_score", "completeness_score"),
        Index("ix_records_source_record_type", "source_id", "record_type"),
    )


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    record_id: Mapped[str | None] = mapped_column(String, ForeignKey("records.id"), nullable=True)
    page_id: Mapped[str | None] = mapped_column(String, ForeignKey("pages.id"), nullable=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String, nullable=True)
    image_type: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    record: Mapped["Record | None"] = relationship(
        "Record",
        back_populates="images",
        foreign_keys=[record_id],
    )
    page: Mapped["Page | None"] = relationship("Page", back_populates="images")

    __table_args__ = (
        UniqueConstraint("record_id", "url"),
        Index("ix_images_tenant_id", "tenant_id"),
        Index("ix_images_record_id", "record_id"),
        Index("ix_images_source_id", "source_id"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="jobs")

    __table_args__ = (
        Index("ix_jobs_tenant_id", "tenant_id"),
        Index("ix_jobs_source_id", "source_id"),
        Index("ix_jobs_status", "status"),
    )


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default="public")
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_tenants_name", "name"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    permissions_json: Mapped[str] = mapped_column(Text, default='["read"]', nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)

    __table_args__ = (
        Index("ix_api_keys_tenant_id", "tenant_id"),
        Index("ix_api_keys_enabled", "enabled"),
    )


class APIUsageEvent(Base):
    __tablename__ = "api_usage_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    api_key_id: Mapped[str] = mapped_column(String, ForeignKey("api_keys.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    __table_args__ = (
        Index("ix_api_usage_events_api_key_id", "api_key_id"),
        Index("ix_api_usage_events_tenant_id", "tenant_id"),
        Index("ix_api_usage_events_endpoint", "endpoint"),
        Index("ix_api_usage_events_created_at", "created_at"),
    )


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    timestamp: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)
    service: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source | None"] = relationship("Source", back_populates="logs")

    __table_args__ = (
        Index("ix_logs_timestamp", "timestamp"),
        Index("ix_logs_level", "level"),
        Index("ix_logs_service", "service"),
        Index("ix_logs_source_id", "source_id"),
    )


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    from_record_id: Mapped[str] = mapped_column(String, ForeignKey("records.id"), nullable=False)
    to_record_id: Mapped[str] = mapped_column(String, ForeignKey("records.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "from_record_id",
            "to_record_id",
            "relationship_type",
            name="uq_entity_relationships_dedup",
        ),
        Index("ix_entity_relationships_source_id", "source_id"),
        Index("ix_entity_relationships_from_record_id", "from_record_id"),
        Index("ix_entity_relationships_to_record_id", "to_record_id"),
        Index("ix_entity_relationships_type", "relationship_type"),
    )


class DuplicateReview(Base):
    __tablename__ = "duplicate_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    left_record_id: Mapped[str] = mapped_column(String, ForeignKey("records.id"), nullable=False)
    right_record_id: Mapped[str] = mapped_column(String, ForeignKey("records.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    similarity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    merge_target_id: Mapped[str | None] = mapped_column(String, ForeignKey("records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "left_record_id",
            "right_record_id",
            name="uq_duplicate_reviews_pair",
        ),
        Index("ix_duplicate_reviews_status", "status"),
        Index("ix_duplicate_reviews_similarity_score", "similarity_score"),
    )


class AuditAction(Base):
    __tablename__ = "audit_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    record_id: Mapped[str | None] = mapped_column(String, ForeignKey("records.id"), nullable=True)
    affected_record_ids: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_actions_action_type", "action_type"),
        Index("ix_audit_actions_created_at", "created_at"),
        Index("ix_audit_actions_record_id", "record_id"),
        Index("ix_audit_actions_source_id", "source_id"),
    )


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    cron_expr: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    source: Mapped["Source | None"] = relationship("Source", back_populates="schedules")

    __table_args__ = (
        Index("ix_scheduled_jobs_source_id", "source_id"),
        Index("ix_scheduled_jobs_job_type", "job_type"),
        Index("ix_scheduled_jobs_enabled", "enabled"),
    )


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    bucket_date: Mapped[str] = mapped_column(String, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("bucket_date", name="uq_metric_snapshots_bucket_date"),
        Index("ix_metric_snapshots_bucket_date", "bucket_date"),
    )


class MergeHistory(Base):
    __tablename__ = "merge_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    primary_record_id: Mapped[str] = mapped_column(String, nullable=False)
    secondary_record_id: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    primary_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    secondary_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    relationships_snapshot: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollback_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    __table_args__ = (
        Index("ix_merge_history_primary_record_id", "primary_record_id"),
        Index("ix_merge_history_secondary_record_id", "secondary_record_id"),
        Index("ix_merge_history_source_id", "source_id"),
    )
