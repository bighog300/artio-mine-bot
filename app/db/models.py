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
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    site_map: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
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
        Index("ix_pages_source_id", "source_id"),
        Index("ix_pages_status", "status"),
        Index("ix_pages_page_type", "page_type"),
    )


class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
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

    # Confidence
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String, default="LOW", nullable=False)
    confidence_reasons: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

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
        Index("ix_records_source_id", "source_id"),
        Index("ix_records_status", "status"),
        Index("ix_records_record_type", "record_type"),
        Index("ix_records_confidence_band", "confidence_band"),
    )


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
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
        Index("ix_images_record_id", "record_id"),
        Index("ix_images_source_id", "source_id"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
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
        Index("ix_jobs_source_id", "source_id"),
        Index("ix_jobs_status", "status"),
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
