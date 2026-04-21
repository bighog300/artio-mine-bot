import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
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
    active_mapping_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    published_mapping_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    active_mapping_preset_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_presets.id"),
        nullable=True,
    )
    runtime_mode: Mapped[str] = mapped_column(String, default="draft_only", nullable=False)
    runtime_ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mapping_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_discovery_run_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    last_mapping_published_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    runtime_mapping_updated_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    mapping_status: Mapped[str] = mapped_column(String, default="none", nullable=False)
    last_mapping_scan_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    last_mapping_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    pages: Mapped[list["Page"]] = relationship("Page", back_populates="source", cascade="all, delete-orphan")
    records: Mapped[list["Record"]] = relationship("Record", back_populates="source", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="source", cascade="all, delete-orphan")
    job_events: Mapped[list["JobEvent"]] = relationship("JobEvent", back_populates="source")
    logs: Mapped[list["Log"]] = relationship("Log", back_populates="source")
    schedules: Mapped[list["ScheduledJob"]] = relationship(
        "ScheduledJob",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    mapping_versions: Mapped[list["SourceMappingVersion"]] = relationship(
        "SourceMappingVersion",
        back_populates="source",
        cascade="all, delete-orphan",
        foreign_keys="SourceMappingVersion.source_id",
    )
    mapping_presets: Mapped[list["SourceMappingPreset"]] = relationship(
        "SourceMappingPreset",
        back_populates="source",
        cascade="all, delete-orphan",
        primaryjoin="Source.id == SourceMappingPreset.source_id",
        foreign_keys="SourceMappingPreset.source_id",
    )
    source_profiles: Mapped[list["SourceProfile"]] = relationship(
        "SourceProfile",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    active_mapping_version: Mapped["SourceMappingVersion | None"] = relationship(
        "SourceMappingVersion",
        foreign_keys=[active_mapping_version_id],
        post_update=True,
    )
    published_mapping_version: Mapped["SourceMappingVersion | None"] = relationship(
        "SourceMappingVersion",
        foreign_keys=[published_mapping_version_id],
        post_update=True,
    )
    active_mapping_preset: Mapped["SourceMappingPreset | None"] = relationship(
        "SourceMappingPreset",
        primaryjoin="Source.active_mapping_preset_id == SourceMappingPreset.id",
        foreign_keys=[active_mapping_preset_id],
        post_update=True,
    )


class SourceProfile(Base):
    __tablename__ = "source_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    seed_url: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    site_fingerprint: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    sitemap_urls: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    nav_discovery_summary: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    profile_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="source_profiles")
    url_families: Mapped[list["UrlFamily"]] = relationship(
        "UrlFamily",
        back_populates="source_profile",
        cascade="all, delete-orphan",
    )
    mapping_versions: Mapped[list["SourceMappingVersion"]] = relationship(
        "SourceMappingVersion",
        back_populates="based_on_profile",
    )

    __table_args__ = (
        Index("ix_source_profiles_source_id_started_at", "source_id", "started_at"),
        Index("ix_source_profiles_source_id_status", "source_id", "status"),
    )


class UrlFamily(Base):
    __tablename__ = "url_families"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_profile_id: Mapped[str] = mapped_column(String, ForeignKey("source_profiles.id"), nullable=False)
    family_key: Mapped[str] = mapped_column(String, nullable=False)
    family_label: Mapped[str] = mapped_column(String, nullable=False)
    path_pattern: Mapped[str] = mapped_column(String, nullable=False)
    page_type_candidate: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_urls_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    follow_policy_candidate: Mapped[str | None] = mapped_column(String, nullable=True)
    pagination_policy_candidate: Mapped[str | None] = mapped_column(String, nullable=True)
    include_by_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    diagnostics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    source_profile: Mapped["SourceProfile"] = relationship("SourceProfile", back_populates="url_families")

    __table_args__ = (
        UniqueConstraint("source_profile_id", "family_key", name="uq_url_families_profile_family"),
        Index("ix_url_families_profile_id_confidence", "source_profile_id", "confidence"),
    )


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    crawl_run_id: Mapped[str | None] = mapped_column(String, ForeignKey("crawl_runs.id"), nullable=True)
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
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    template_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    classification_method: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    review_status: Mapped[str | None] = mapped_column(String, nullable=True)
    mapping_version_id_used: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="pages")
    records: Mapped[list["Record"]] = relationship("Record", back_populates="page")
    images: Mapped[list["Image"]] = relationship("Image", back_populates="page")

    __table_args__ = (
        UniqueConstraint("source_id", "url"),
        Index("ix_pages_tenant_id", "tenant_id"),
        Index("ix_pages_source_id", "source_id"),
        Index("ix_pages_crawl_run_id", "crawl_run_id"),
        Index("ix_pages_status", "status"),
        Index("ix_pages_page_type", "page_type"),
    )


class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    crawl_run_id: Mapped[str | None] = mapped_column(String, ForeignKey("crawl_runs.id"), nullable=True)
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
    completeness_details: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
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
        Index("ix_records_crawl_run_id", "crawl_run_id"),
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
    crawl_run_id: Mapped[str | None] = mapped_column(String, ForeignKey("crawl_runs.id"), nullable=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    current_item: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    last_log_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="jobs")
    events: Mapped[list["JobEvent"]] = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_tenant_id", "tenant_id"),
        Index("ix_jobs_source_id", "source_id"),
        Index("ix_jobs_crawl_run_id", "crawl_run_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_worker_id", "worker_id"),
    )


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    seed_url: Mapped[str] = mapped_column(String, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cooldown_until: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    stats_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    mapping_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_crawl_runs_source_id_status", "source_id", "status"),
        Index("ix_crawl_runs_last_heartbeat_at", "last_heartbeat_at"),
    )


class CrawlFrontier(Base):
    __tablename__ = "crawl_frontier"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    crawl_run_id: Mapped[str] = mapped_column(String, ForeignKey("crawl_runs.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    mapping_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    normalized_url: Mapped[str] = mapped_column(String, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
    family_key: Mapped[str | None] = mapped_column(String, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discovered_from_url: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    predicted_page_type: Mapped[str | None] = mapped_column(String, nullable=True)
    discovered_from_page_type: Mapped[str | None] = mapped_column(String, nullable=True)
    discovery_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="discovered", nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    leased_by_worker: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    next_eligible_fetch_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String, nullable=True)
    first_discovered_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    last_extracted_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    diagnostics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "mapping_version_id",
            "normalized_url",
            name="uq_crawl_frontier_source_mapping_normalized_url",
        ),
        Index("ix_crawl_frontier_crawl_run_id_status", "crawl_run_id", "status"),
        Index("ix_crawl_frontier_crawl_run_priority_depth_created", "crawl_run_id", "priority", "depth", "created_at"),
        Index("ix_crawl_frontier_lease_expires_at", "lease_expires_at"),
        Index("ix_crawl_frontier_next_retry_at", "next_retry_at"),
    )


class CrawlRunCheckpoint(Base):
    __tablename__ = "crawl_run_checkpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    crawl_run_id: Mapped[str] = mapped_column(String, ForeignKey("crawl_runs.id"), nullable=False, unique=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    mapping_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    last_checkpoint_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    frontier_counts_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    progress_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    last_processed_url: Mapped[str | None] = mapped_column(String, nullable=True)
    worker_state_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_crawl_run_checkpoints_crawl_run_id", "crawl_run_id"),
        Index("ix_crawl_run_checkpoints_status", "status"),
        Index("ix_crawl_run_checkpoints_last_checkpoint_at", "last_checkpoint_at"),
    )


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    level: Mapped[str] = mapped_column(String, default="info", nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="events")
    source: Mapped["Source | None"] = relationship("Source", back_populates="job_events")

    __table_args__ = (
        Index("ix_job_events_job_id_timestamp", "job_id", "timestamp"),
        Index("ix_job_events_source_id_timestamp", "source_id", "timestamp"),
        Index("ix_job_events_event_type", "event_type"),
        Index("ix_job_events_worker_id_timestamp", "worker_id", "timestamp"),
    )


class WorkerState(Base):
    __tablename__ = "worker_states"

    worker_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="idle", nullable=False)
    current_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_worker_states_status", "status"),
        Index("ix_worker_states_last_heartbeat_at", "last_heartbeat_at"),
    )


class SourceMappingVersion(Base):
    __tablename__ = "source_mapping_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    based_on_profile_id: Mapped[str | None] = mapped_column(String, ForeignKey("source_profiles.id"), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    scan_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    scan_options_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    published_by: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="mapping_versions",
        foreign_keys=[source_id],
    )
    based_on_profile: Mapped["SourceProfile | None"] = relationship(
        "SourceProfile",
        back_populates="mapping_versions",
    )
    page_types: Mapped[list["SourceMappingPageType"]] = relationship(
        "SourceMappingPageType",
        back_populates="mapping_version",
        cascade="all, delete-orphan",
    )
    rows: Mapped[list["SourceMappingRow"]] = relationship(
        "SourceMappingRow",
        back_populates="mapping_version",
        cascade="all, delete-orphan",
    )
    samples: Mapped[list["SourceMappingSample"]] = relationship(
        "SourceMappingSample",
        back_populates="mapping_version",
        cascade="all, delete-orphan",
    )
    sample_runs: Mapped[list["SourceMappingSampleRun"]] = relationship(
        "SourceMappingSampleRun",
        back_populates="mapping_version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("source_id", "version_number", name="uq_source_mapping_versions_source_version"),
        Index("ix_source_mapping_versions_source_id", "source_id"),
        Index("ix_source_mapping_versions_source_status", "source_id", "status"),
    )


class SourceMappingPageType(Base):
    __tablename__ = "source_mapping_page_types"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    mapping_version_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    classifier_signals_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    mapping_version: Mapped["SourceMappingVersion"] = relationship("SourceMappingVersion", back_populates="page_types")
    samples: Mapped[list["SourceMappingSample"]] = relationship("SourceMappingSample", back_populates="page_type")
    rows: Mapped[list["SourceMappingRow"]] = relationship("SourceMappingRow", back_populates="page_type")

    __table_args__ = (
        UniqueConstraint("mapping_version_id", "key", name="uq_source_mapping_page_types_version_key"),
        Index("ix_source_mapping_page_types_version_id", "mapping_version_id"),
    )


class SourceMappingSample(Base):
    __tablename__ = "source_mapping_samples"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    mapping_version_id: Mapped[str] = mapped_column(String, ForeignKey("source_mapping_versions.id"), nullable=False)
    page_id: Mapped[str | None] = mapped_column(String, ForeignKey("pages.id"), nullable=True)
    page_type_id: Mapped[str | None] = mapped_column(String, ForeignKey("source_mapping_page_types.id"), nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    html_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    dom_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    mapping_version: Mapped["SourceMappingVersion"] = relationship("SourceMappingVersion", back_populates="samples")
    page_type: Mapped["SourceMappingPageType | None"] = relationship("SourceMappingPageType", back_populates="samples")

    __table_args__ = (
        Index("ix_source_mapping_samples_mapping_version_id", "mapping_version_id"),
        Index("ix_source_mapping_samples_page_type_id", "page_type_id"),
    )


class SourceMappingRow(Base):
    __tablename__ = "source_mapping_rows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    mapping_version_id: Mapped[str] = mapped_column(String, ForeignKey("source_mapping_versions.id"), nullable=False)
    page_type_id: Mapped[str | None] = mapped_column(String, ForeignKey("source_mapping_page_types.id"), nullable=True)
    selector: Mapped[str] = mapped_column(String, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String, nullable=False, default="css")
    extraction_mode: Mapped[str] = mapped_column(String, nullable=False, default="text")
    attribute_name: Mapped[str | None] = mapped_column(String, nullable=True)
    sample_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_entity: Mapped[str] = mapped_column(String, nullable=False)
    destination_field: Mapped[str] = mapped_column(String, nullable=False)
    category_target: Mapped[str | None] = mapped_column(String, nullable=True)
    transforms_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String, nullable=False, default="proposed")
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    mapping_version: Mapped["SourceMappingVersion"] = relationship("SourceMappingVersion", back_populates="rows")
    page_type: Mapped["SourceMappingPageType | None"] = relationship("SourceMappingPageType", back_populates="rows")

    __table_args__ = (
        Index("ix_source_mapping_rows_mapping_version_id", "mapping_version_id"),
        Index("ix_source_mapping_rows_mapping_version_status", "mapping_version_id", "status"),
        Index("ix_source_mapping_rows_mapping_version_destination_entity", "mapping_version_id", "destination_entity"),
        Index("ix_source_mapping_rows_page_type_destination", "page_type_id", "destination_entity", "destination_field"),
    )


class SourceMappingSampleRun(Base):
    __tablename__ = "source_mapping_sample_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    mapping_version_id: Mapped[str] = mapped_column(String, ForeignKey("source_mapping_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    mapping_version: Mapped["SourceMappingVersion"] = relationship("SourceMappingVersion", back_populates="sample_runs")
    results: Mapped[list["SourceMappingSampleResult"]] = relationship(
        "SourceMappingSampleResult",
        back_populates="sample_run",
        cascade="all, delete-orphan",
    )


class SourceMappingSampleResult(Base):
    __tablename__ = "source_mapping_sample_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    sample_run_id: Mapped[str] = mapped_column(String, ForeignKey("source_mapping_sample_runs.id"), nullable=False)
    sample_id: Mapped[str | None] = mapped_column(String, ForeignKey("source_mapping_samples.id"), nullable=True)
    record_preview_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    sample_run: Mapped["SourceMappingSampleRun"] = relationship("SourceMappingSampleRun", back_populates="results")


class SourceMappingPreset(Base):
    __tablename__ = "source_mapping_presets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_from_mapping_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_mapping_versions.id"),
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_type_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="mapping_presets",
        primaryjoin="SourceMappingPreset.source_id == Source.id",
        foreign_keys=[source_id],
    )
    rows: Mapped[list["SourceMappingPresetRow"]] = relationship(
        "SourceMappingPresetRow",
        back_populates="preset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("source_id", "name", name="uq_source_mapping_presets_source_name"),
        Index("ix_source_mapping_presets_source_id_created_at", "source_id", "created_at"),
    )


class SourceMappingPresetRow(Base):
    __tablename__ = "source_mapping_preset_rows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    preset_id: Mapped[str] = mapped_column(String, ForeignKey("source_mapping_presets.id", ondelete="CASCADE"), nullable=False)
    page_type_key: Mapped[str | None] = mapped_column(String, nullable=True)
    page_type_label: Mapped[str | None] = mapped_column(String, nullable=True)
    selector: Mapped[str] = mapped_column(String, nullable=False)
    pattern_type: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    attribute_name: Mapped[str | None] = mapped_column(String, nullable=True)
    destination_entity: Mapped[str | None] = mapped_column(String, nullable=True)
    destination_field: Mapped[str | None] = mapped_column(String, nullable=True)
    category_target: Mapped[str | None] = mapped_column(String, nullable=True)
    transforms_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rationale_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    preset: Mapped["SourceMappingPreset"] = relationship("SourceMappingPreset", back_populates="rows")

    __table_args__ = (
        Index("ix_source_mapping_preset_rows_preset_id_sort_order", "preset_id", "sort_order"),
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


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    record_id: Mapped[str | None] = mapped_column(String, ForeignKey("records.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_entity_type", "entity_type"),
        Index("ix_audit_events_entity_id", "entity_id"),
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_record_id", "record_id"),
        Index("ix_audit_events_source_id", "source_id"),
        Index("ix_audit_events_user_id", "user_id"),
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


class BackfillCampaign(Base):
    """Tracks backfill campaigns for auditing and monitoring."""

    __tablename__ = "backfill_campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    name: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_updates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_updates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)

    jobs: Mapped[list["BackfillJob"]] = relationship(
        "BackfillJob",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_backfill_campaigns_tenant_id", "tenant_id"),
        Index("ix_backfill_campaigns_status", "status"),
        Index("ix_backfill_campaigns_created_at", "created_at"),
    )


class BackfillJob(Base):
    """Individual backfill job for a record."""

    __tablename__ = "backfill_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    campaign_id: Mapped[str] = mapped_column(String, ForeignKey("backfill_campaigns.id"), nullable=False)
    record_id: Mapped[str] = mapped_column(String, ForeignKey("records.id"), nullable=False)
    url_to_crawl: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    before_completeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_completeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fields_updated: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)

    campaign: Mapped["BackfillCampaign"] = relationship("BackfillCampaign", back_populates="jobs")
    record: Mapped["Record"] = relationship("Record")

    __table_args__ = (
        Index("ix_backfill_jobs_tenant_id", "tenant_id"),
        Index("ix_backfill_jobs_campaign_id", "campaign_id"),
        Index("ix_backfill_jobs_record_id", "record_id"),
        Index("ix_backfill_jobs_status", "status"),
    )


class BackfillSchedule(Base):
    """Scheduled backfill campaign template."""

    __tablename__ = "backfill_schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    name: Mapped[str] = mapped_column(String, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String, nullable=False, default="recurring")
    cron_expression: Mapped[str | None] = mapped_column(String, nullable=True)
    filters_json: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_start: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_backfill_schedules_tenant_id", "tenant_id"),
        Index("ix_backfill_schedules_enabled", "enabled"),
        Index("ix_backfill_schedules_next_run_at", "next_run_at"),
    )


class BackfillPolicy(Base):
    """Automation rules for backfill triggering."""

    __tablename__ = "backfill_policies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    name: Mapped[str] = mapped_column(String, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    conditions_json: Mapped[str] = mapped_column(Text, nullable=False)
    action_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_backfill_policies_tenant_id", "tenant_id"),
        Index("ix_backfill_policies_enabled", "enabled"),
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
