import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: list[Any]
    total: int
    skip: int
    limit: int


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------

class SourceStats(BaseModel):
    pending_records: int = 0
    approved_records: int = 0
    rejected_records: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0


class SourceCreate(BaseModel):
    url: str
    name: str | None = None
    crawl_intent: str = "site_root"
    max_pages: int | None = None
    crawl_hints: dict[str, Any] | None = None
    extraction_rules: dict[str, Any] | None = None
    max_depth: int | None = None
    enabled: bool = True


class SourceUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    operational_status: str | None = None
    crawl_intent: str | None = None
    crawl_hints: dict[str, Any] | None = None
    extraction_rules: dict[str, Any] | None = None
    max_depth: int | None = None
    max_pages: int | None = None
    enabled: bool | None = None
    queue_paused: bool | None = None
    health_status: str | None = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    url: str
    name: str | None
    status: str
    operational_status: str = "idle"
    total_pages: int
    total_records: int
    last_crawled_at: datetime | None
    created_at: datetime
    crawl_hints: dict[str, Any] | None = None
    extraction_rules: dict[str, Any] | None = None
    crawl_intent: str = "site_root"
    max_depth: int | None = None
    max_pages: int | None = None
    enabled: bool = True
    queue_paused: bool = False
    health_status: str = "unknown"
    stats: SourceStats | None = None

    @field_validator("crawl_hints", mode="before")
    @classmethod
    def parse_crawl_hints(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @field_validator("extraction_rules", mode="before")
    @classmethod
    def parse_extraction_rules(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v


class SourceDetailResponse(SourceResponse):
    site_map: str | None = None
    error_message: str | None = None
    updated_at: datetime


class SourceActionResponse(BaseModel):
    source_id: str
    status: str
    operational_status: str
    queued_jobs: int = 0


class MappingDraftCreateRequest(BaseModel):
    scan_mode: str = "standard"
    allowed_paths: list[str] = []
    blocked_paths: list[str] = []
    max_pages: int = 50
    max_depth: int = 3
    sample_pages_per_type: int = 5


class MappingDraftSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_id: str
    version_number: int
    status: str
    scan_status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    page_type_count: int = 0
    mapping_count: int = 0
    approved_count: int = 0
    needs_review_count: int = 0


class MappingPageTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    key: str
    label: str
    sample_count: int
    confidence_score: float


class MappingRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    mapping_version_id: str
    page_type_id: str | None
    selector: str
    extraction_mode: str
    sample_value: str | None
    destination_entity: str
    destination_field: str
    category_target: str | None
    confidence_score: float
    status: str
    is_required: bool
    is_enabled: bool
    sort_order: int
    transforms: list[str] = []
    rationale: list[str] = []


class MappingRowUpdateRequest(BaseModel):
    destination_entity: str | None = None
    destination_field: str | None = None
    category_target: str | None = None
    status: str | None = None
    is_enabled: bool | None = None
    is_required: bool | None = None
    sort_order: int | None = None
    transforms: list[str] | None = None
    rationale: list[str] | None = None


class MappingRowActionRequest(BaseModel):
    row_ids: list[str]
    action: str


class MappingPreviewRequest(BaseModel):
    sample_page_id: str


class MappingExtractionPreview(BaseModel):
    mapping_row_id: str
    source_selector: str
    raw_value: str | None
    normalized_value: str | None
    destination_entity: str
    destination_field: str
    category_target: str | None
    confidence_score: float
    warning: str | None = None


class MappingPreviewResponse(BaseModel):
    sample_page_id: str
    page_url: str
    page_type_key: str | None
    extractions: list[MappingExtractionPreview]
    record_preview: dict[str, Any]


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------

class MineStartRequest(BaseModel):
    max_depth: int | None = None
    max_pages: int | None = None
    sections: list[str] | None = None


class MineStartResponse(BaseModel):
    job_id: str
    source_id: str
    status: str
    message: str


class MineStatusProgress(BaseModel):
    pages_crawled: int
    pages_total_estimated: int
    pages_eligible_for_extraction: int
    pages_classified: int
    pages_skipped: int
    pages_error: int
    records_extracted: int
    records_by_type: dict[str, int]
    images_collected: int
    percent_complete: int


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_type: str
    status: str
    started_at: datetime | None = None


class MineStatusResponse(BaseModel):
    source_id: str
    status: str
    current_job: JobSummary | None = None
    progress: MineStatusProgress | None = None


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class PageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_id: str
    url: str
    page_type: str
    status: str
    title: str | None
    depth: int
    fetch_method: str | None
    crawled_at: datetime | None
    record_count: int = 0


class PageDetailResponse(PageResponse):
    html: str | None
    original_url: str
    error_message: str | None
    created_at: datetime
    extracted_at: datetime | None


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------

class RecordListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_id: str
    record_type: str
    status: str
    title: str | None
    description: str | None
    confidence_score: int
    confidence_band: str
    confidence_reasons: list[str] = []
    source_url: str | None
    image_count: int = 0
    primary_image_url: str | None = None
    created_at: datetime

    @field_validator("confidence_reasons", mode="before")
    @classmethod
    def parse_confidence_reasons(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    url: str
    image_type: str
    alt_text: str | None
    confidence: int
    is_valid: bool
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None


class RecordDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_id: str
    record_type: str
    status: str
    title: str | None
    description: str | None
    source_url: str | None

    # Event/Exhibition
    start_date: str | None = None
    end_date: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    artist_names: list[str] = []
    ticket_url: str | None = None
    is_free: bool | None = None
    price_text: str | None = None
    curator: str | None = None

    # Artist
    bio: str | None = None
    nationality: str | None = None
    birth_year: int | None = None
    mediums: list[str] = []
    collections: list[str] = []
    website_url: str | None = None
    instagram_url: str | None = None
    email: str | None = None
    avatar_url: str | None = None

    # Venue
    address: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    opening_hours: str | None = None

    # Artwork
    medium: str | None = None
    year: int | None = None
    dimensions: str | None = None
    price: str | None = None

    confidence_score: int
    confidence_band: str
    confidence_reasons: list[str] = []
    admin_notes: str | None = None
    primary_image_id: str | None = None
    images: list[ImageResponse] = []
    created_at: datetime
    updated_at: datetime
    exported_at: datetime | None = None

    @field_validator("artist_names", "mediums", "collections", "confidence_reasons", mode="before")
    @classmethod
    def parse_json_array(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []


class RecordUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    artist_names: list[str] | None = None
    ticket_url: str | None = None
    is_free: bool | None = None
    price_text: str | None = None
    curator: str | None = None
    bio: str | None = None
    nationality: str | None = None
    birth_year: int | None = None
    mediums: list[str] | None = None
    collections: list[str] | None = None
    website_url: str | None = None
    instagram_url: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    opening_hours: str | None = None
    medium: str | None = None
    year: int | None = None
    dimensions: str | None = None
    price: str | None = None
    admin_notes: str | None = None


class ApproveResponse(BaseModel):
    id: str
    status: str


class RejectRequest(BaseModel):
    reason: str | None = None


class BulkApproveRequest(BaseModel):
    source_id: str
    min_confidence: int = 70
    record_type: str | None = None


class BulkApproveResponse(BaseModel):
    approved_count: int


class SetPrimaryImageRequest(BaseModel):
    image_id: str


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

class ValidateImagesRequest(BaseModel):
    urls: list[str]


class ImageValidationResult(BaseModel):
    url: str
    is_valid: bool
    mime_type: str | None = None
    status_code: int | None = None
    error: str | None = None


class ValidateImagesResponse(BaseModel):
    results: list[ImageValidationResult]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class ExportPreviewByType(BaseModel):
    artist: int = 0
    event: int = 0
    exhibition: int = 0
    venue: int = 0
    artwork: int = 0


class ExportPreviewResponse(BaseModel):
    record_count: int
    by_type: ExportPreviewByType
    artio_configured: bool


class ExportPushRequest(BaseModel):
    source_id: str | None = None
    record_ids: list[str] = []


class ExportPushResponse(BaseModel):
    exported_count: int
    failed_count: int
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class SourceStats2(BaseModel):
    total: int
    active: int
    done: int


class RecordStats(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    exported: int
    by_type: dict[str, int]
    by_confidence: dict[str, int]


class PageStats(BaseModel):
    total: int
    crawled: int
    error: int


class GlobalStats(BaseModel):
    sources: SourceStats2
    records: RecordStats
    pages: PageStats


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_id: str
    job_type: str
    status: str
    error_message: str | None
    attempts: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

class ConflictResolveRequest(BaseModel):
    field: str
    selected_value: Any


class ArtistReviewListItem(BaseModel):
    id: str
    source_id: str
    title: str | None = None
    completeness_score: int = 0
    missing_fields: list[str] = []
    has_conflicts: bool = False
    conflict_fields: list[str] = []


class ArtistReviewResponse(BaseModel):
    id: str
    source_id: str
    title: str | None = None
    canonical_fields: dict[str, Any] = {}
    completeness_score: int = 0
    missing_fields: list[str] = []
    provenance: dict[str, Any] = {}
    conflicts: dict[str, Any] = {}
    related: dict[str, list[dict[str, Any]]] = {}
