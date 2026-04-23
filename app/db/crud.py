import json
import hashlib
import math
import re
from asyncio import sleep
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import Select, and_, delete, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import cosine_similarity, create_embedding
from app.db.models import (
    APIKey,
    APIUsageEvent,
    CrawlFrontier,
    CrawlRun,
    CrawlRunCheckpoint,
    DomainRateLimit,
    ExtractionBaseline,
    AuditAction,
    AuditEvent,
    DuplicateReview,
    Entity,
    EntityLink,
    EntityRelationship,
    Image,
    Job,
    JobEvent,
    MergeHistory,
    MetricSnapshot,
    MappingTemplate,
    MappingDriftSignal,
    MappingRepairProposal,
    Page,
    Record,
    ScheduledJob,
    Source,
    SourceProfile,
    SourceMappingPageType,
    SourceMappingPreset,
    SourceMappingPresetRow,
    SourceMappingRow,
    SourceMappingSample,
    SourceMappingSampleResult,
    SourceMappingSampleRun,
    SourceMappingVersion,
    Tenant,
    UrlFamily,
    WorkerState,
)
from app.crawler.url_utils import normalize_url
from app.records.deduplication import (
    build_merge_snapshot,
    classify_identity_match,
    fuzzy_name_match,
    merge_record,
    normalize_name,
    normalize_record_type,
    prepare_record_payload,
)

logger = structlog.get_logger()
TERMINAL_JOB_STATUSES = {"done", "completed", "failed", "cancelled"}
TERMINAL_CRAWL_RUN_STATUSES = {"completed", "failed", "cancelled"}
FRONTIER_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"queued", "skipped", "failed_terminal"},
    "queued": {"fetching", "completed", "skipped", "failed_retryable", "failed_terminal"},
    "fetching": {"queued", "fetched", "parsed", "extracted", "completed", "failed_retryable", "failed_terminal", "skipped"},
    "fetched": {"parsed", "extracted", "completed", "skipped", "failed_retryable", "failed_terminal"},
    "parsed": {"extracted", "completed", "queued", "failed_retryable", "failed_terminal", "skipped"},
    "extracted": set(),
    "completed": set(),
    "skipped": {"queued", "fetching"},
    "failed_retryable": {"queued", "fetching", "failed_terminal", "skipped"},
    "failed_terminal": {"queued"},
}

MAPPING_ALLOWED_FIELDS: dict[str, set[str]] = {
    "artist": {"title", "description", "bio", "nationality", "birth_year", "website_url", "instagram_url", "email"},
    "event": {"title", "description", "start_date", "end_date", "venue_name", "venue_address", "ticket_url", "price_text"},
    "exhibition": {"title", "description", "start_date", "end_date", "venue_name", "venue_address", "curator"},
    "venue": {"title", "description", "address", "city", "country", "phone", "opening_hours"},
    "artwork": {"title", "description", "medium", "year", "dimensions", "price"},
    "organization": {"title", "description", "website_url", "url", "address", "city", "country"},
}
DRIFT_SIGNAL_STATUSES = {"open", "acknowledged", "resolved", "dismissed"}
DRIFT_SIGNAL_SEVERITIES = {"low", "medium", "high"}
DRIFT_SIGNAL_TYPES = {"FIELD_MISSING", "FIELD_EMPTY", "STRUCTURE_CHANGED", "SELECTOR_FAIL", "VALUE_ANOMALY"}
MAPPING_REPAIR_STATUSES = {"DRAFT", "VALIDATED", "REJECTED", "APPLIED"}


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _extract_completeness_and_conflicts(raw_data: str | None) -> tuple[int, bool]:
    if not raw_data:
        return 0, False
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        return 0, False
    completeness = payload.get("completeness_score", 0)
    has_conflicts = bool(payload.get("conflicts", {}))
    return int(completeness or 0), has_conflicts


def _record_text_for_embedding(record_type: str, values: dict[str, Any]) -> str:
    segments: list[str] = []
    if record_type == "artist":
        for key in ("title", "bio", "nationality", "city", "country", "description"):
            value = values.get(key)
            if value:
                segments.append(str(value))
        for key in ("mediums", "collections"):
            value = values.get(key)
            if isinstance(value, list):
                segments.extend(str(item) for item in value)
    elif record_type == "exhibition":
        for key in ("title", "description", "venue_name", "venue_address", "city", "country"):
            value = values.get(key)
            if value:
                segments.append(str(value))
    elif record_type in {"artist_article", "article"}:
        for key in ("title", "description", "source_url"):
            value = values.get(key)
            if value:
                segments.append(str(value))
    return " ".join(segments)


def _build_embedding_payload(record_type: str, values: dict[str, Any]) -> str | None:
    text = _record_text_for_embedding(record_type, values)
    if not text.strip():
        return None
    return json.dumps(create_embedding(text))


def _ordered_pair(left_record_id: str, right_record_id: str) -> tuple[str, str]:
    return (left_record_id, right_record_id) if left_record_id <= right_record_id else (right_record_id, left_record_id)


def serialize_record_snapshot(record: Record) -> dict[str, Any]:
    fields = [
        "id", "source_id", "page_id", "job_id", "record_type", "normalized_name", "fingerprint", "fingerprint_version", "status", "title", "description", "source_url",
        "start_date", "end_date", "venue_name", "venue_address", "artist_names", "ticket_url", "is_free",
        "price_text", "curator", "bio", "nationality", "birth_year", "mediums", "collections", "website_url",
        "instagram_url", "email", "avatar_url", "address", "city", "country", "phone", "opening_hours",
        "medium", "year", "dimensions", "price", "raw_data", "structured_data", "field_confidence", "raw_error", "extraction_model",
        "extraction_provider", "embedding_vector", "confidence_score", "confidence_band", "confidence_reasons",
        "completeness_score", "has_conflicts", "admin_notes", "primary_image_id", "exported_at",
    ]
    snapshot: dict[str, Any] = {}
    json_fields = {"artist_names", "mediums", "collections", "confidence_reasons"}
    for field in fields:
        value = getattr(record, field)
        if isinstance(value, datetime):
            snapshot[field] = value.isoformat()
        elif field in json_fields and isinstance(value, str):
            try:
                snapshot[field] = json.loads(value)
            except json.JSONDecodeError:
                snapshot[field] = []
        else:
            snapshot[field] = value
    return snapshot

# ---------------------------------------------------------------------------
# Source CRUD
# ---------------------------------------------------------------------------


async def create_source(
    db: AsyncSession,
    url: str,
    name: str | None = None,
    tenant_id: str = "public",
    crawl_hints: str | None = None,
    extraction_rules: str | None = None,
    crawl_intent: str = "site_root",
    max_depth: int | None = None,
    max_pages: int | None = None,
    enabled: bool = True,
) -> Source:
    await ensure_tenant(db, tenant_id, name=tenant_id)
    source = Source(
        tenant_id=tenant_id,
        url=url,
        name=name,
        crawl_hints=crawl_hints,
        extraction_rules=extraction_rules,
        crawl_intent=crawl_intent,
        max_depth=max_depth,
        max_pages=max_pages,
        enabled=enabled,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def get_source(db: AsyncSession, source_id: str) -> Source | None:
    result = await db.execute(select(Source).where(Source.id == source_id))
    return result.scalar_one_or_none()


async def create_source_profile(db: AsyncSession, source_id: str, seed_url: str) -> SourceProfile:
    profile = SourceProfile(source_id=source_id, seed_url=seed_url, status="running")
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def finalize_source_profile(
    db: AsyncSession,
    profile_id: str,
    *,
    status: str,
    site_fingerprint: dict[str, Any],
    sitemap_urls: list[str],
    nav_discovery_summary: dict[str, Any],
    profile_metrics: dict[str, Any],
) -> SourceProfile:
    result = await db.execute(select(SourceProfile).where(SourceProfile.id == profile_id))
    profile = result.scalar_one()
    profile.status = status
    profile.completed_at = datetime.now(UTC)
    profile.site_fingerprint = json.dumps(site_fingerprint)
    profile.sitemap_urls = json.dumps(sitemap_urls)
    profile.nav_discovery_summary = json.dumps(nav_discovery_summary)
    profile.profile_metrics_json = json.dumps(profile_metrics)
    await db.commit()
    await db.refresh(profile)
    return profile


async def replace_url_families(
    db: AsyncSession,
    *,
    profile_id: str,
    families: list[dict[str, Any]],
) -> list[UrlFamily]:
    await db.execute(delete(UrlFamily).where(UrlFamily.source_profile_id == profile_id))
    created: list[UrlFamily] = []
    for family in families:
        row = UrlFamily(
            source_profile_id=profile_id,
            family_key=family["family_key"],
            family_label=family["family_label"],
            path_pattern=family["path_pattern"],
            page_type_candidate=family["page_type_candidate"],
            confidence=float(family["confidence"]),
            sample_urls_json=json.dumps(family.get("sample_urls", [])),
            follow_policy_candidate=family.get("follow_policy_candidate"),
            pagination_policy_candidate=family.get("pagination_policy_candidate"),
            include_by_default=bool(family.get("include_by_default", True)),
            diagnostics_json=json.dumps(family.get("diagnostics", {})),
        )
        db.add(row)
        created.append(row)
    await db.commit()
    for row in created:
        await db.refresh(row)
    return created


async def get_source_profile(db: AsyncSession, source_id: str, profile_id: str) -> SourceProfile | None:
    result = await db.execute(
        select(SourceProfile)
        .where(SourceProfile.id == profile_id, SourceProfile.source_id == source_id)
    )
    return result.scalar_one_or_none()


async def list_url_families(db: AsyncSession, profile_id: str) -> list[UrlFamily]:
    result = await db.execute(
        select(UrlFamily)
        .where(UrlFamily.source_profile_id == profile_id)
        .order_by(UrlFamily.confidence.desc(), UrlFamily.path_pattern.asc())
    )
    return list(result.scalars().all())


async def create_mapping_suggestion_draft(
    db: AsyncSession,
    *,
    source_id: str,
    profile_id: str,
    mapping_json: dict[str, Any],
    tenant_id: str = "public",
    created_by: str | None = None,
) -> SourceMappingVersion:
    profile = await get_source_profile(db, source_id, profile_id)
    if profile is None:
        raise ValueError("Profile not found")
    current = await db.execute(
        select(func.max(SourceMappingVersion.version_number)).where(SourceMappingVersion.source_id == source_id)
    )
    next_version = int(current.scalar_one_or_none() or 0) + 1
    mapping_version = SourceMappingVersion(
        source_id=source_id,
        tenant_id=tenant_id,
        based_on_profile_id=profile_id,
        version_number=next_version,
        status="draft",
        scan_status="completed",
        created_by=created_by,
        mapping_json=json.dumps(mapping_json),
        summary_json=json.dumps(
            {
                "family_rule_count": len(mapping_json.get("family_rules", [])),
                "generation_mode": "deterministic",
            }
        ),
    )
    db.add(mapping_version)
    await db.commit()
    await db.refresh(mapping_version)
    return mapping_version


async def get_mapping_suggestion_draft(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_id: str,
) -> SourceMappingVersion | None:
    result = await db.execute(
        select(SourceMappingVersion).where(
            SourceMappingVersion.id == mapping_id,
            SourceMappingVersion.source_id == source_id,
        )
    )
    return result.scalar_one_or_none()


async def update_mapping_suggestion_draft_family_rules(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_id: str,
    family_updates: list[dict[str, Any]],
) -> SourceMappingVersion:
    version = await get_mapping_suggestion_draft(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise ValueError("Mapping version not found")
    if version.status != "draft":
        raise ValueError("Only draft mappings are editable")

    mapping_json = json.loads(version.mapping_json or "{}")
    rules = mapping_json.get("family_rules", [])
    by_key = {rule.get("family_key"): rule for rule in rules if isinstance(rule, dict)}
    for update in family_updates:
        family_key = update.get("family_key")
        if family_key not in by_key:
            raise ValueError(f"Family '{family_key}' not found in mapping")
        target = by_key[family_key]
        for field in (
            "page_type",
            "include",
            "follow_links",
            "crawl_priority",
            "pagination_mode",
            "freshness_policy",
            "rationale",
            "family_label",
        ):
            if field in update and update[field] is not None:
                target[field] = update[field]

    mapping_json["family_rules"] = list(by_key.values())
    version.mapping_json = json.dumps(mapping_json)
    version.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(version)
    return version


async def approve_mapping_suggestion_version(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_id: str,
    approved_by: str | None = None,
) -> SourceMappingVersion:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError("Source not found")
    version = await get_mapping_suggestion_draft(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise ValueError("Mapping version not found")
    if version.status != "draft":
        raise ValueError("Only draft mappings can be approved")

    now = datetime.now(UTC)
    existing = await db.execute(
        select(SourceMappingVersion).where(
            SourceMappingVersion.source_id == source_id,
            SourceMappingVersion.id != mapping_id,
            SourceMappingVersion.is_active.is_(True),
        )
    )
    for row in list(existing.scalars().all()):
        row.is_active = False
        row.status = "superseded"
        row.superseded_at = now
        row.updated_at = now

    version.status = "approved"
    version.is_active = True
    version.approved_at = now
    version.approved_by = approved_by
    version.published_at = now
    version.published_by = approved_by
    version.updated_at = now

    source.active_mapping_version_id = version.id
    source.published_mapping_version_id = version.id
    source.mapping_status = "published"
    source.last_mapping_published_at = now
    source.updated_at = now
    await db.commit()
    await db.refresh(version)
    return version


async def get_source_by_url(db: AsyncSession, url: str) -> Source | None:
    result = await db.execute(select(Source).where(Source.url == url))
    return result.scalar_one_or_none()


async def wait_for_source(
    db: AsyncSession,
    source_id: str,
    *,
    retries: int = 3,
    delay_seconds: float = 0.2,
) -> Source | None:
    """Wait briefly for source visibility across transactions/processes."""
    for attempt in range(retries):
        source = await get_source(db, source_id)
        if source is not None:
            return source
        if attempt < retries - 1:
            await sleep(delay_seconds)
    return None


async def list_sources(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    enabled: bool | None = None,
) -> list[Source]:
    stmt = select(Source)
    if enabled is not None:
        stmt = stmt.where(Source.enabled == enabled)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_source(db: AsyncSession, source_id: str, **kwargs: Any) -> Source:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    for key, value in kwargs.items():
        setattr(source, key, value)
    source.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(source)
    return source


async def delete_source(db: AsyncSession, source_id: str) -> bool:
    source = await get_source(db, source_id)
    if source is None:
        return False
    await db.delete(source)
    await db.commit()
    return True


async def get_source_stats(db: AsyncSession, source_id: str) -> dict[str, Any]:
    pending = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.status == "pending"
        )
    )
    approved = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.status == "approved"
        )
    )
    rejected = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.status == "rejected"
        )
    )
    high = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.confidence_band == "HIGH"
        )
    )
    medium = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.confidence_band == "MEDIUM"
        )
    )
    low = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.confidence_band == "LOW"
        )
    )
    return {
        "pending_records": pending.scalar_one(),
        "approved_records": approved.scalar_one(),
        "rejected_records": rejected.scalar_one(),
        "high_confidence": high.scalar_one(),
        "medium_confidence": medium.scalar_one(),
        "low_confidence": low.scalar_one(),
    }


async def set_source_operational_status(
    db: AsyncSession,
    source_id: str,
    operational_status: str,
    *,
    queue_paused: bool | None = None,
    error_message: str | None = None,
) -> Source:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    source.operational_status = operational_status
    source.status = operational_status
    if queue_paused is not None:
        source.queue_paused = queue_paused
    if error_message is not None:
        source.error_message = error_message
    source.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(source)
    return source


async def cancel_non_terminal_jobs_for_source(db: AsyncSession, source_id: str) -> int:
    stmt = select(Job).where(
        Job.source_id == source_id,
        Job.status.in_(["queued", "pending", "running", "paused"]),
    )
    rows = (await db.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    for job in rows:
        job.status = "cancelled"
        job.completed_at = now
    await db.commit()
    return len(rows)


async def retry_failed_jobs_for_source(db: AsyncSession, source_id: str) -> int:
    stmt = select(Job).where(Job.source_id == source_id, Job.status == "failed")
    rows = (await db.execute(stmt)).scalars().all()
    for job in rows:
        job.status = "pending"
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        job.attempts = int(job.attempts or 0) + 1
    await db.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Source Mapper CRUD
# ---------------------------------------------------------------------------


async def create_source_mapping_version(
    db: AsyncSession,
    source_id: str,
    *,
    tenant_id: str = "public",
    scan_options: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> SourceMappingVersion:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    current = await db.execute(
        select(func.max(SourceMappingVersion.version_number)).where(SourceMappingVersion.source_id == source_id)
    )
    next_version = int(current.scalar_one_or_none() or 0) + 1
    mapping_version = SourceMappingVersion(
        source_id=source_id,
        tenant_id=tenant_id,
        version_number=next_version,
        status="draft",
        scan_status="completed",
        scan_options_json=json.dumps(scan_options or {}),
        created_by=created_by,
    )
    db.add(mapping_version)
    source.mapping_status = "draft"
    source.last_mapping_scan_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(mapping_version)
    return mapping_version


async def get_source_mapping_version(db: AsyncSession, source_id: str, draft_id: str) -> SourceMappingVersion | None:
    result = await db.execute(
        select(SourceMappingVersion).where(
            SourceMappingVersion.id == draft_id,
            SourceMappingVersion.source_id == source_id,
        )
    )
    return result.scalar_one_or_none()


async def list_source_mapping_versions(db: AsyncSession, source_id: str) -> list[SourceMappingVersion]:
    result = await db.execute(
        select(SourceMappingVersion)
        .where(SourceMappingVersion.source_id == source_id)
        .order_by(SourceMappingVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def list_source_mapping_rows(
    db: AsyncSession,
    source_id: str,
    draft_id: str,
    *,
    page_type_key: str | None = None,
    status: str | None = None,
    destination_entity: str | None = None,
    min_confidence: float | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SourceMappingRow]:
    stmt = (
        select(SourceMappingRow)
        .join(SourceMappingVersion, SourceMappingRow.mapping_version_id == SourceMappingVersion.id)
        .where(SourceMappingVersion.source_id == source_id, SourceMappingVersion.id == draft_id)
    )
    if page_type_key:
        stmt = stmt.join(SourceMappingPageType, SourceMappingRow.page_type_id == SourceMappingPageType.id).where(
            SourceMappingPageType.key == page_type_key
        )
    if status:
        stmt = stmt.where(SourceMappingRow.status == status)
    if destination_entity:
        stmt = stmt.where(SourceMappingRow.destination_entity == destination_entity)
    if min_confidence is not None:
        stmt = stmt.where(SourceMappingRow.confidence_score >= min_confidence)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def list_source_mapping_page_types(db: AsyncSession, draft_id: str) -> list[SourceMappingPageType]:
    result = await db.execute(
        select(SourceMappingPageType).where(SourceMappingPageType.mapping_version_id == draft_id)
    )
    return list(result.scalars().all())


async def clear_source_mapping_draft_data(db: AsyncSession, draft_id: str) -> None:
    await db.execute(delete(SourceMappingSampleResult).where(
        SourceMappingSampleResult.sample_run_id.in_(
            select(SourceMappingSampleRun.id).where(SourceMappingSampleRun.mapping_version_id == draft_id)
        )
    ))
    await db.execute(delete(SourceMappingSampleRun).where(SourceMappingSampleRun.mapping_version_id == draft_id))
    await db.execute(delete(SourceMappingRow).where(SourceMappingRow.mapping_version_id == draft_id))
    await db.execute(delete(SourceMappingSample).where(SourceMappingSample.mapping_version_id == draft_id))
    await db.execute(delete(SourceMappingPageType).where(SourceMappingPageType.mapping_version_id == draft_id))
    await db.commit()


async def update_source_mapping_row(
    db: AsyncSession,
    source_id: str,
    draft_id: str,
    row_id: str,
    **kwargs: Any,
) -> SourceMappingRow:
    result = await db.execute(
        select(SourceMappingRow)
        .join(SourceMappingVersion, SourceMappingRow.mapping_version_id == SourceMappingVersion.id)
        .where(SourceMappingVersion.source_id == source_id, SourceMappingVersion.id == draft_id, SourceMappingRow.id == row_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError("Mapping row not found")
    if "destination_entity" in kwargs and kwargs["destination_entity"] is not None:
        entity = kwargs["destination_entity"]
        field = kwargs.get("destination_field", row.destination_field)
        if entity not in MAPPING_ALLOWED_FIELDS or field not in MAPPING_ALLOWED_FIELDS[entity]:
            raise ValueError(f"Invalid destination '{entity}.{field}'")
    if "destination_field" in kwargs and kwargs["destination_field"] is not None and "destination_entity" not in kwargs:
        if row.destination_entity not in MAPPING_ALLOWED_FIELDS or kwargs["destination_field"] not in MAPPING_ALLOWED_FIELDS[row.destination_entity]:
            raise ValueError(f"Invalid destination '{row.destination_entity}.{kwargs['destination_field']}'")
    for key, value in kwargs.items():
        if key == "transforms" and value is not None:
            row.transforms_json = json.dumps(value)
        elif key == "rationale" and value is not None:
            row.confidence_reasons_json = json.dumps(value)
        elif hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return row


async def clone_published_mapping_to_draft(
    db: AsyncSession,
    source_id: str,
    *,
    created_by: str | None = None,
) -> SourceMappingVersion:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    if not source.active_mapping_version_id:
        raise ValueError("No active published mapping exists")

    published = await get_source_mapping_version(db, source_id, source.active_mapping_version_id)
    if published is None or published.status != "published":
        raise ValueError("No active published mapping exists")

    draft = await create_source_mapping_version(
        db,
        source_id,
        tenant_id=published.tenant_id,
        scan_options=json.loads(published.scan_options_json or "{}"),
        created_by=created_by,
    )

    src_page_types = await list_source_mapping_page_types(db, published.id)
    page_type_map: dict[str, str] = {}
    for src in src_page_types:
        cloned = await create_source_mapping_page_type(
            db,
            draft.id,
            key=src.key,
            label=src.label,
            sample_count=src.sample_count,
            confidence_score=src.confidence_score,
        )
        page_type_map[src.id] = cloned.id

    src_rows = await list_source_mapping_rows(db, source_id, published.id, skip=0, limit=2_000)
    for row in src_rows:
        await create_source_mapping_row(
            db,
            draft.id,
            page_type_id=page_type_map.get(row.page_type_id) if row.page_type_id else None,
            selector=row.selector,
            sample_value=row.sample_value,
            destination_entity=row.destination_entity,
            destination_field=row.destination_field,
            confidence_score=row.confidence_score,
            status="changed_from_published",
            rationale=json.loads(row.confidence_reasons_json or "[]"),
        )
    return draft


async def create_drift_remap_draft(
    db: AsyncSession,
    *,
    source_id: str,
    generated_from_signal_id: str | None = None,
    created_by: str | None = None,
) -> SourceMappingVersion:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    if not source.active_mapping_version_id:
        raise ValueError("No active mapping available for remap draft generation")
    draft = await clone_published_mapping_to_draft(db, source_id, created_by=created_by)
    summary = json.loads(draft.summary_json or "{}") if draft.summary_json else {}
    summary["drift_triggered"] = True
    summary["generated_from_signal_id"] = generated_from_signal_id
    summary["based_on_active_mapping_version"] = source.active_mapping_version_id
    summary["generated_at"] = datetime.now(UTC).isoformat()
    draft.summary_json = json.dumps(summary)
    await db.commit()
    await db.refresh(draft)
    return draft


async def set_source_mapping_rows_status(
    db: AsyncSession,
    source_id: str,
    draft_id: str,
    row_ids: list[str],
    *,
    status: str | None = None,
    is_enabled: bool | None = None,
) -> int:
    rows = await list_source_mapping_rows(db, source_id, draft_id, skip=0, limit=max(len(row_ids), 1_000))
    row_map = {row.id: row for row in rows}
    now = datetime.now(UTC)
    updated = 0
    for row_id in row_ids:
        row = row_map.get(row_id)
        if row is None:
            continue
        if status is not None:
            row.status = status
        if is_enabled is not None:
            row.is_enabled = is_enabled
        row.updated_at = now
        updated += 1
    if updated > 0:
        await db.commit()
    return updated


async def publish_source_mapping_version(
    db: AsyncSession,
    source_id: str,
    draft_id: str,
    *,
    published_by: str | None = None,
) -> SourceMappingVersion:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    draft = await get_source_mapping_version(db, source_id, draft_id)
    if draft is None:
        raise ValueError("Mapping draft not found")
    if draft.status == "published":
        return draft

    now = datetime.now(UTC)
    enabled_rows = (
        await db.execute(
            select(SourceMappingRow).where(
                SourceMappingRow.mapping_version_id == draft_id,
                SourceMappingRow.is_enabled.is_(True),
            )
        )
    ).scalars().all()
    approved_enabled_rows = [row for row in enabled_rows if row.status == "approved"]
    if not approved_enabled_rows:
        all_unreviewed = bool(enabled_rows) and all(
            row.status in {"proposed", "needs_review"} for row in enabled_rows
        )
        if all_unreviewed:
            for row in enabled_rows:
                row.status = "approved"
                row.updated_at = now
        else:
            raise RuntimeError("No approved rows — approve at least one mapping row before publishing")

    previous_active_id = source.active_mapping_version_id
    if previous_active_id:
        previous_active = await get_source_mapping_version(db, source_id, previous_active_id)
        if previous_active is not None and previous_active.id != draft_id and previous_active.status == "published":
            previous_active.status = "superseded"
            previous_active.updated_at = now

    draft.status = "published"
    draft.scan_status = "completed"
    draft.published_at = now
    draft.published_by = published_by
    draft.updated_at = now
    source.active_mapping_version_id = draft.id
    source.published_mapping_version_id = draft.id
    source.mapping_status = "published"
    source.runtime_mode = "deterministic_runtime"
    source.runtime_ai_enabled = False
    source.mapping_stale = False
    source.last_mapping_published_at = now
    page_types = await list_source_mapping_page_types(db, draft.id)
    page_type_lookup = {page_type.id: page_type for page_type in page_types}
    runtime_rows: list[SourceMappingPresetRow] = []
    for row in enabled_rows:
        page_type = page_type_lookup.get(row.page_type_id)
        runtime_rows.append(
            SourceMappingPresetRow(
                preset_id="published-runtime",
                page_type_key=page_type.key if page_type else "unknown",
                page_type_label=page_type.label if page_type else "Unknown",
                selector=row.selector,
                pattern_type=row.pattern_type,
                extraction_mode=row.extraction_mode,
                attribute_name=row.attribute_name,
                destination_entity=row.destination_entity,
                destination_field=row.destination_field,
                category_target=row.category_target,
                transforms_json=row.transforms_json,
                confidence_score=row.confidence_score,
                is_required=row.is_required,
                is_enabled=row.is_enabled,
                sort_order=row.sort_order,
                rationale_json=row.confidence_reasons_json,
            )
        )
    existing_runtime_map: dict[str, Any] | None = None
    if source.structure_map:
        try:
            parsed = json.loads(source.structure_map)
            if isinstance(parsed, dict):
                existing_runtime_map = parsed
        except json.JSONDecodeError:
            existing_runtime_map = None
    runtime_map = build_runtime_map_from_preset_rows(
        SourceMappingPreset(source_id=source_id, tenant_id=source.tenant_id, name="published-mapping-runtime"),
        runtime_rows,
        base_runtime_map=existing_runtime_map,
        source_url=source.url,
    )
    runtime_map["runtime_map_source"] = "published_mapping"
    runtime_map["published_mapping_version_id"] = draft.id
    source.structure_map = json.dumps(runtime_map)
    source.runtime_mapping_updated_at = now
    source.updated_at = now
    await db.commit()
    await db.refresh(draft)
    return draft


async def create_mapping_drift_signal(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_version_id: str | None,
    signal_type: str,
    severity: str,
    family_key: str | None = None,
    metrics: dict[str, Any] | None = None,
    diagnostics: dict[str, Any] | None = None,
    sample_urls: list[str] | None = None,
    proposed_action: str | None = None,
    dedupe_hours: int = 12,
    page_id: str | None = None,
    record_id: str | None = None,
    field_name: str | None = None,
    mapping_field: str | None = None,
    selector_path: str | None = None,
    failing_selector: str | None = None,
    drift_type: str | None = None,
    previous_value: str | None = None,
    current_value: str | None = None,
    confidence: float | None = None,
) -> MappingDriftSignal:
    if severity not in DRIFT_SIGNAL_SEVERITIES:
        raise ValueError(f"Invalid drift severity '{severity}'")
    normalized_drift_type = drift_type or signal_type.upper()
    if normalized_drift_type not in DRIFT_SIGNAL_TYPES:
        normalized_drift_type = "VALUE_ANOMALY"
    if dedupe_hours > 0:
        cutoff = datetime.now(UTC) - timedelta(hours=dedupe_hours)
        existing_stmt = select(MappingDriftSignal).where(
            MappingDriftSignal.source_id == source_id,
            MappingDriftSignal.mapping_version_id == mapping_version_id,
            MappingDriftSignal.signal_type == signal_type,
            MappingDriftSignal.status.in_(["open", "acknowledged"]),
            MappingDriftSignal.detected_at >= cutoff,
        )
        if family_key is None:
            existing_stmt = existing_stmt.where(MappingDriftSignal.family_key.is_(None))
        else:
            existing_stmt = existing_stmt.where(MappingDriftSignal.family_key == family_key)
        existing = (await db.execute(existing_stmt.order_by(MappingDriftSignal.detected_at.desc()))).scalar_one_or_none()
        if existing is not None:
            existing.severity = severity
            existing.metrics_json = json.dumps(metrics or {})
            existing.diagnostics_json = json.dumps(diagnostics or {})
            existing.sample_urls_json = json.dumps(sample_urls or [])
            existing.proposed_action = proposed_action
            existing.page_id = page_id
            existing.record_id = record_id
            existing.field_name = field_name
            existing.mapping_field = mapping_field
            existing.selector_path = selector_path
            existing.failing_selector = failing_selector
            existing.drift_type = normalized_drift_type
            existing.previous_value = previous_value
            existing.current_value = current_value
            existing.confidence = confidence
            existing.detected_at = datetime.now(UTC)
            existing.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(existing)
            return existing

    signal = MappingDriftSignal(
        source_id=source_id,
        mapping_version_id=mapping_version_id,
        page_id=page_id,
        record_id=record_id,
        field_name=field_name,
        mapping_field=mapping_field,
        selector_path=selector_path,
        failing_selector=failing_selector,
        drift_type=normalized_drift_type,
        family_key=family_key,
        signal_type=signal_type,
        severity=severity,
        confidence=confidence,
        previous_value=previous_value,
        current_value=current_value,
        metrics_json=json.dumps(metrics or {}),
        diagnostics_json=json.dumps(diagnostics or {}),
        sample_urls_json=json.dumps(sample_urls or []),
        proposed_action=proposed_action,
        status="open",
        detected_at=datetime.now(UTC),
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)
    return signal


async def list_mapping_drift_signals(
    db: AsyncSession,
    *,
    source_id: str,
    status: str | None = None,
    severity: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[MappingDriftSignal]:
    stmt = select(MappingDriftSignal).where(MappingDriftSignal.source_id == source_id)
    if status:
        stmt = stmt.where(MappingDriftSignal.status == status)
    if severity:
        stmt = stmt.where(MappingDriftSignal.severity == severity)
    stmt = stmt.order_by(MappingDriftSignal.detected_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_mapping_drift_signal(
    db: AsyncSession,
    *,
    source_id: str,
    signal_id: str,
) -> MappingDriftSignal | None:
    stmt = select(MappingDriftSignal).where(
        MappingDriftSignal.source_id == source_id,
        MappingDriftSignal.id == signal_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def update_mapping_drift_signal_status(
    db: AsyncSession,
    *,
    source_id: str,
    signal_id: str,
    status: str,
    resolution_notes: str | None = None,
) -> MappingDriftSignal:
    if status not in DRIFT_SIGNAL_STATUSES:
        raise ValueError(f"Invalid drift status '{status}'")
    signal = await get_mapping_drift_signal(db, source_id=source_id, signal_id=signal_id)
    if signal is None:
        raise ValueError("Drift signal not found")
    now = datetime.now(UTC)
    signal.status = status
    signal.updated_at = now
    if resolution_notes is not None:
        signal.resolution_notes = resolution_notes
    if status == "acknowledged":
        signal.acknowledged_at = now
    if status in {"resolved", "dismissed"}:
        signal.resolved_at = now
    await db.commit()
    await db.refresh(signal)
    return signal


async def create_mapping_repair_proposal(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_version_id: str | None,
    field_name: str,
    old_selector: str | None,
    proposed_selector: str,
    confidence_score: float,
    supporting_pages: list[str],
    drift_signals_used: list[str],
    validation_results: dict[str, Any],
    occurrence_count: int = 1,
    priority_score: float = 0.0,
    strategy_used: str | None = None,
    reasoning: str | None = None,
    evidence: dict[str, Any] | None = None,
    status: str = "DRAFT",
) -> MappingRepairProposal:
    if status not in MAPPING_REPAIR_STATUSES:
        raise ValueError(f"Invalid mapping repair status '{status}'")
    proposal = MappingRepairProposal(
        source_id=source_id,
        mapping_version_id=mapping_version_id,
        field_name=field_name,
        old_selector=old_selector,
        proposed_selector=proposed_selector,
        confidence_score=confidence_score,
        supporting_pages_json=json.dumps(supporting_pages),
        drift_signals_used_json=json.dumps(drift_signals_used),
        validation_results_json=json.dumps(validation_results),
        occurrence_count=max(1, int(occurrence_count)),
        priority_score=float(priority_score),
        strategy_used=strategy_used,
        reasoning=reasoning,
        evidence_json=json.dumps(evidence or {}),
        status=status,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return proposal


async def upsert_mapping_repair_proposal(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_version_id: str | None,
    field_name: str,
    old_selector: str | None,
    proposed_selector: str,
    confidence_score: float,
    supporting_pages: list[str],
    drift_signals_used: list[str],
    validation_results: dict[str, Any],
    occurrence_count: int = 1,
    priority_score: float = 0.0,
    strategy_used: str | None = None,
    reasoning: str | None = None,
    evidence: dict[str, Any] | None = None,
    status: str = "DRAFT",
) -> MappingRepairProposal:
    stmt = select(MappingRepairProposal).where(
        MappingRepairProposal.source_id == source_id,
        MappingRepairProposal.mapping_version_id == mapping_version_id,
        MappingRepairProposal.field_name == field_name,
        MappingRepairProposal.proposed_selector == proposed_selector,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is None:
        return await create_mapping_repair_proposal(
            db,
            source_id=source_id,
            mapping_version_id=mapping_version_id,
            field_name=field_name,
            old_selector=old_selector,
            proposed_selector=proposed_selector,
            confidence_score=confidence_score,
            supporting_pages=supporting_pages,
            drift_signals_used=drift_signals_used,
            validation_results=validation_results,
            occurrence_count=occurrence_count,
            priority_score=priority_score,
            strategy_used=strategy_used,
            reasoning=reasoning,
            evidence=evidence,
            status=status,
        )

    existing.confidence_score = max(existing.confidence_score, confidence_score)
    existing.status = "VALIDATED" if "VALIDATED" in {existing.status, status} else status
    existing.validation_results_json = json.dumps(validation_results)
    existing.occurrence_count = max(1, int(existing.occurrence_count or 1) + max(1, int(occurrence_count)))
    existing.priority_score = max(float(existing.priority_score or 0.0), float(priority_score))
    if strategy_used:
        existing.strategy_used = strategy_used
    if reasoning:
        existing.reasoning = reasoning
    existing.evidence_json = json.dumps(evidence or {})
    existing.updated_at = datetime.now(UTC)

    existing_pages = set(json.loads(existing.supporting_pages_json or "[]"))
    existing_pages.update(supporting_pages)
    existing.supporting_pages_json = json.dumps(sorted(existing_pages)[:25])

    existing_signals = set(json.loads(existing.drift_signals_used_json or "[]"))
    existing_signals.update(drift_signals_used)
    existing.drift_signals_used_json = json.dumps(sorted(existing_signals)[:100])

    await db.commit()
    await db.refresh(existing)
    return existing


async def list_mapping_repair_proposals(
    db: AsyncSession,
    *,
    source_id: str,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[MappingRepairProposal]:
    stmt = select(MappingRepairProposal).where(MappingRepairProposal.source_id == source_id)
    if status:
        stmt = stmt.where(MappingRepairProposal.status == status)
    stmt = (
        stmt.order_by(
            MappingRepairProposal.priority_score.desc(),
            MappingRepairProposal.occurrence_count.desc(),
            MappingRepairProposal.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_mapping_repair_proposal(
    db: AsyncSession,
    *,
    source_id: str,
    proposal_id: str,
) -> MappingRepairProposal | None:
    stmt = select(MappingRepairProposal).where(
        MappingRepairProposal.source_id == source_id,
        MappingRepairProposal.id == proposal_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def update_mapping_repair_proposal(
    db: AsyncSession,
    *,
    source_id: str,
    proposal_id: str,
    status: str | None = None,
    reviewed_by: str | None = None,
    validation_results: dict[str, Any] | None = None,
    feedback: dict[str, Any] | None = None,
    applied_mapping_version_id: str | None = None,
    confidence_score: float | None = None,
) -> MappingRepairProposal:
    proposal = await get_mapping_repair_proposal(db, source_id=source_id, proposal_id=proposal_id)
    if proposal is None:
        raise ValueError("Mapping repair proposal not found")
    if status is not None:
        if status not in MAPPING_REPAIR_STATUSES:
            raise ValueError(f"Invalid mapping repair status '{status}'")
        proposal.status = status
    if validation_results is not None:
        proposal.validation_results_json = json.dumps(validation_results)
    if feedback is not None:
        proposal.feedback_json = json.dumps(feedback)
    if reviewed_by is not None:
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = datetime.now(UTC)
    if applied_mapping_version_id is not None:
        proposal.applied_mapping_version_id = applied_mapping_version_id
    if confidence_score is not None:
        proposal.confidence_score = float(confidence_score)
    proposal.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(proposal)
    return proposal


async def get_mapping_repair_feedback_stats(
    db: AsyncSession,
    *,
    source_id: str,
    field_name: str,
) -> dict[str, float]:
    stmt = select(MappingRepairProposal).where(
        MappingRepairProposal.source_id == source_id,
        MappingRepairProposal.field_name == field_name,
    )
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return {"accepted_rate": 0.5, "apply_success_rate": 0.5}

    accepted = sum(1 for row in rows if row.status in {"VALIDATED", "APPLIED"})
    applied = [row for row in rows if row.status == "APPLIED"]
    successful_applies = 0
    for row in applied:
        feedback = json.loads(row.feedback_json or "{}")
        event = feedback.get("post_apply_success")
        if isinstance(event, dict):
            successful_applies += 1

    accepted_rate = accepted / max(len(rows), 1)
    apply_success_rate = successful_applies / max(len(applied), 1) if applied else 0.5
    return {
        "accepted_rate": round(accepted_rate, 4),
        "apply_success_rate": round(apply_success_rate, 4),
    }


async def get_mapping_health_state(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_version_id: str | None,
) -> str:
    stmt = select(MappingDriftSignal).where(
        MappingDriftSignal.source_id == source_id,
        MappingDriftSignal.status.in_(["open", "acknowledged"]),
    )
    if mapping_version_id:
        stmt = stmt.where(MappingDriftSignal.mapping_version_id == mapping_version_id)
    signals = list((await db.execute(stmt)).scalars().all())
    high_count = sum(1 for item in signals if item.severity == "high")
    medium_count = sum(1 for item in signals if item.severity == "medium")
    if high_count > 0 or len(signals) >= 3:
        return "stale"
    if medium_count > 0:
        return "warning"
    return "healthy"


async def get_extraction_baseline(
    db: AsyncSession,
    *,
    source_id: str,
    page_id: str,
) -> ExtractionBaseline | None:
    stmt = select(ExtractionBaseline).where(
        ExtractionBaseline.source_id == source_id,
        ExtractionBaseline.page_id == page_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_extraction_baseline(
    db: AsyncSession,
    *,
    source_id: str,
    page_id: str,
    mapping_version_id: str | None,
    record_id: str | None,
    baseline: dict[str, Any],
    field_stats: dict[str, Any],
    dom_section_hash: str | None,
    confidence_score: int | None,
) -> ExtractionBaseline:
    current = await get_extraction_baseline(db, source_id=source_id, page_id=page_id)
    if current is None:
        current = ExtractionBaseline(
            source_id=source_id,
            page_id=page_id,
            mapping_version_id=mapping_version_id,
            record_id=record_id,
            baseline_json=json.dumps(baseline),
            field_stats_json=json.dumps(field_stats),
            dom_section_hash=dom_section_hash,
            confidence_score=confidence_score,
            updated_at=datetime.now(UTC),
        )
        db.add(current)
    else:
        current.mapping_version_id = mapping_version_id
        current.record_id = record_id
        current.baseline_json = json.dumps(baseline)
        current.field_stats_json = json.dumps(field_stats)
        current.dom_section_hash = dom_section_hash
        current.confidence_score = confidence_score
        current.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(current)
    return current


async def create_source_mapping_page_type(
    db: AsyncSession,
    draft_id: str,
    *,
    key: str,
    label: str,
    sample_count: int = 0,
    confidence_score: float = 0.0,
) -> SourceMappingPageType:
    page_type = SourceMappingPageType(
        mapping_version_id=draft_id,
        key=key,
        label=label,
        sample_count=sample_count,
        confidence_score=confidence_score,
    )
    db.add(page_type)
    await db.commit()
    await db.refresh(page_type)
    return page_type


async def create_source_mapping_sample(
    db: AsyncSession,
    draft_id: str,
    *,
    page_type_id: str | None,
    url: str,
    title: str | None = None,
    html_snapshot: str | None = None,
) -> SourceMappingSample:
    sample = SourceMappingSample(
        mapping_version_id=draft_id,
        page_type_id=page_type_id,
        url=url,
        title=title,
        html_snapshot=html_snapshot,
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


async def create_source_mapping_row(
    db: AsyncSession,
    draft_id: str,
    *,
    page_type_id: str | None,
    selector: str,
    sample_value: str | None,
    destination_entity: str,
    destination_field: str,
    confidence_score: float = 0.5,
    status: str = "proposed",
    rationale: list[str] | None = None,
) -> SourceMappingRow:
    row = SourceMappingRow(
        mapping_version_id=draft_id,
        page_type_id=page_type_id,
        selector=selector,
        sample_value=sample_value,
        destination_entity=destination_entity,
        destination_field=destination_field,
        confidence_score=confidence_score,
        status=status,
        confidence_reasons_json=json.dumps(rationale or []),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_source_mapping_sample(db: AsyncSession, sample_id: str) -> SourceMappingSample | None:
    result = await db.execute(select(SourceMappingSample).where(SourceMappingSample.id == sample_id))
    return result.scalar_one_or_none()


async def create_source_mapping_sample_run(
    db: AsyncSession,
    draft_id: str,
    *,
    sample_count: int,
    created_by: str | None = None,
    status: str = "completed",
    summary: dict[str, Any] | None = None,
) -> SourceMappingSampleRun:
    sample_run = SourceMappingSampleRun(
        mapping_version_id=draft_id,
        sample_count=sample_count,
        status=status,
        created_by=created_by,
        completed_at=datetime.now(UTC) if status == "completed" else None,
        summary_json=json.dumps(summary or {}),
    )
    db.add(sample_run)
    await db.commit()
    await db.refresh(sample_run)
    return sample_run


async def create_source_mapping_sample_result(
    db: AsyncSession,
    sample_run_id: str,
    *,
    sample_id: str | None = None,
    record_preview: dict[str, Any] | None = None,
    review_status: str = "pending",
) -> SourceMappingSampleResult:
    result = SourceMappingSampleResult(
        sample_run_id=sample_run_id,
        sample_id=sample_id,
        record_preview_json=json.dumps(record_preview or {}),
        review_status=review_status,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


async def get_source_mapping_sample_run(
    db: AsyncSession,
    source_id: str,
    draft_id: str,
    sample_run_id: str,
) -> SourceMappingSampleRun | None:
    stmt = (
        select(SourceMappingSampleRun)
        .join(SourceMappingVersion, SourceMappingSampleRun.mapping_version_id == SourceMappingVersion.id)
        .where(
            SourceMappingVersion.source_id == source_id,
            SourceMappingVersion.id == draft_id,
            SourceMappingSampleRun.id == sample_run_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_source_mapping_sample_results(
    db: AsyncSession,
    sample_run_id: str,
    *,
    review_status: str | None = None,
) -> list[SourceMappingSampleResult]:
    stmt = select(SourceMappingSampleResult).where(SourceMappingSampleResult.sample_run_id == sample_run_id)
    if review_status:
        stmt = stmt.where(SourceMappingSampleResult.review_status == review_status)
    stmt = stmt.order_by(SourceMappingSampleResult.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_source_mapping_sample_result(
    db: AsyncSession,
    source_id: str,
    draft_id: str,
    sample_run_id: str,
    result_id: str,
    *,
    review_status: str | None = None,
    review_notes: str | None = None,
) -> SourceMappingSampleResult:
    stmt = (
        select(SourceMappingSampleResult)
        .join(SourceMappingSampleRun, SourceMappingSampleResult.sample_run_id == SourceMappingSampleRun.id)
        .join(SourceMappingVersion, SourceMappingSampleRun.mapping_version_id == SourceMappingVersion.id)
        .where(
            SourceMappingVersion.source_id == source_id,
            SourceMappingVersion.id == draft_id,
            SourceMappingSampleRun.id == sample_run_id,
            SourceMappingSampleResult.id == result_id,
        )
    )
    result = (await db.execute(stmt)).scalar_one_or_none()
    if result is None:
        raise ValueError("Sample run result not found")
    if review_status is not None:
        result.review_status = review_status
    if review_notes is not None:
        result.review_notes = review_notes
    result.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(result)
    return result


async def rollback_source_mapping_version(
    db: AsyncSession,
    source_id: str,
    version_id: str,
    *,
    rolled_back_by: str | None = None,
) -> SourceMappingVersion:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    version = await get_source_mapping_version(db, source_id, version_id)
    if version is None:
        raise ValueError("Mapping version not found")
    if version.status != "published":
        raise RuntimeError("Rollback requires a published mapping version")

    source.active_mapping_version_id = version.id
    source.mapping_status = "published"
    source.updated_at = datetime.now(UTC)
    version.published_by = rolled_back_by or version.published_by
    await db.commit()
    await db.refresh(version)
    return version


async def list_source_mapping_presets(
    db: AsyncSession,
    source_id: str,
    tenant_id: str = "public",
) -> list[SourceMappingPreset]:
    result = await db.execute(
        select(SourceMappingPreset)
        .where(SourceMappingPreset.source_id == source_id, SourceMappingPreset.tenant_id == tenant_id)
        .order_by(SourceMappingPreset.created_at.desc())
    )
    return list(result.scalars().all())


def validate_mapping_template(template_json: dict[str, Any] | str) -> dict[str, Any]:
    payload: dict[str, Any]
    errors: list[dict[str, Any]] = []
    if isinstance(template_json, str):
        try:
            parsed = json.loads(template_json)
        except json.JSONDecodeError:
            return {"ok": False, "errors": [{"code": "invalid_json", "message": "Template payload is not valid JSON"}]}
        if not isinstance(parsed, dict):
            return {"ok": False, "errors": [{"code": "invalid_structure", "message": "Template payload must be a JSON object"}]}
        payload = parsed
    elif isinstance(template_json, dict):
        payload = template_json
    else:
        return {"ok": False, "errors": [{"code": "invalid_structure", "message": "Template payload must be a JSON object"}]}

    crawl_plan = payload.get("crawl_plan")
    if not isinstance(crawl_plan, dict):
        errors.append({"code": "missing_crawl_plan", "message": "Missing crawl_plan object"})
    else:
        phases = crawl_plan.get("phases")
        if not isinstance(phases, list) or len(phases) == 0:
            errors.append({"code": "empty_phases", "message": "crawl_plan.phases must be a non-empty list"})

    has_extraction_rules = isinstance(payload.get("extraction_rules"), dict) and bool(payload.get("extraction_rules"))
    has_mining_map = isinstance(payload.get("mining_map"), dict) and bool(payload.get("mining_map"))
    has_page_type_rules = isinstance(payload.get("page_type_rules"), dict) and bool(payload.get("page_type_rules"))
    if not (has_extraction_rules or has_mining_map or has_page_type_rules):
        errors.append(
            {
                "code": "invalid_structure",
                "message": "Template must include at least one of extraction_rules, mining_map, or page_type_rules",
            }
        )

    extraction_rules = payload.get("extraction_rules")
    if isinstance(extraction_rules, dict):
        for page_key, rule in extraction_rules.items():
            if not isinstance(rule, dict):
                errors.append(
                    {"code": "invalid_structure", "message": f"extraction_rules.{page_key} must be an object"}
                )
                continue
            selectors = rule.get("css_selectors", {})
            if selectors is None:
                continue
            if not isinstance(selectors, dict):
                errors.append(
                    {
                        "code": "invalid_selector_format",
                        "message": f"extraction_rules.{page_key}.css_selectors must be an object",
                    }
                )
                continue
            for field, selector in selectors.items():
                if not isinstance(selector, str) or not selector.strip():
                    errors.append(
                        {
                            "code": "invalid_selector_format",
                            "message": f"Selector for extraction_rules.{page_key}.css_selectors.{field} must be a non-empty string",
                        }
                    )

    return {"ok": len(errors) == 0, "errors": errors}


async def create_mapping_template(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
    template_json: dict[str, Any],
    schema_version: int = 1,
    created_by: str | None = None,
    is_system: bool = False,
) -> MappingTemplate:
    template = MappingTemplate(
        name=name,
        description=description,
        template_json=template_json,
        schema_version=schema_version,
        created_by=created_by,
        is_system=is_system,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def list_mapping_templates(db: AsyncSession) -> list[MappingTemplate]:
    result = await db.execute(select(MappingTemplate).order_by(MappingTemplate.created_at.desc()))
    return list(result.scalars().all())


async def get_mapping_template(db: AsyncSession, template_id: str) -> MappingTemplate | None:
    result = await db.execute(select(MappingTemplate).where(MappingTemplate.id == template_id))
    return result.scalar_one_or_none()


async def export_source_mapping_preset(
    db: AsyncSession,
    *,
    preset_id: str,
) -> dict[str, Any]:
    preset_result = await db.execute(select(SourceMappingPreset).where(SourceMappingPreset.id == preset_id))
    preset = preset_result.scalar_one_or_none()
    if preset is None:
        raise ValueError("Mapping preset not found")
    rows_result = await db.execute(
        select(SourceMappingPresetRow).where(SourceMappingPresetRow.preset_id == preset.id).order_by(SourceMappingPresetRow.sort_order.asc())
    )
    rows = list(rows_result.scalars().all())
    source = await get_source(db, preset.source_id)
    runtime_map = build_runtime_map_from_preset_rows(
        preset,
        rows,
        source_url=source.url if source else None,
    )
    return {
        "schema_version": 1,
        "name": preset.name,
        "description": preset.description,
        "template_type": "mapping_preset",
        "payload": runtime_map,
    }


async def apply_mapping_template_to_source(
    db: AsyncSession,
    *,
    source_id: str,
    template_id: str,
) -> Source:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError("Source not found")
    template = await get_mapping_template(db, template_id)
    if template is None:
        raise ValueError("Mapping template not found")
    validation = validate_mapping_template(template.template_json)
    if not validation["ok"]:
        raise ValueError("Mapping template is invalid")

    source.structure_map = json.dumps(template.template_json)
    source.active_mapping_preset_id = None
    source.runtime_mapping_updated_at = datetime.now(UTC)
    source.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(source)
    return source


async def get_source_mapping_preset(
    db: AsyncSession,
    preset_id: str,
    source_id: str,
    tenant_id: str = "public",
) -> SourceMappingPreset | None:
    result = await db.execute(
        select(SourceMappingPreset).where(
            SourceMappingPreset.id == preset_id,
            SourceMappingPreset.source_id == source_id,
            SourceMappingPreset.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def create_source_mapping_preset(
    db: AsyncSession,
    source_id: str,
    tenant_id: str,
    name: str,
    description: str | None,
    created_from_mapping_version_id: str | None,
    created_by: str | None,
    row_count: int,
    page_type_count: int,
    summary_json: str | None = None,
) -> SourceMappingPreset:
    preset = SourceMappingPreset(
        tenant_id=tenant_id,
        source_id=source_id,
        name=name,
        description=description,
        created_from_mapping_version_id=created_from_mapping_version_id,
        created_by=created_by,
        row_count=row_count,
        page_type_count=page_type_count,
        summary_json=summary_json,
    )
    db.add(preset)
    await db.flush()
    await db.refresh(preset)
    return preset


async def delete_source_mapping_preset(
    db: AsyncSession,
    preset_id: str,
    source_id: str,
    tenant_id: str = "public",
) -> bool:
    preset = await get_source_mapping_preset(db, preset_id, source_id, tenant_id)
    if preset is None:
        return False
    await db.delete(preset)
    await db.commit()
    return True


async def create_source_mapping_preset_from_version(
    db: AsyncSession,
    *,
    source_id: str,
    tenant_id: str = "public",
    name: str,
    description: str | None = None,
    draft_id: str | None = None,
    mapping_version_id: str | None = None,
    include_statuses: list[str] | None = None,
    created_by: str | None = None,
) -> SourceMappingPreset:
    source = await get_source(db, source_id)
    if source is None or source.tenant_id != tenant_id:
        raise ValueError("Source not found")

    target_version_id = mapping_version_id or draft_id
    if target_version_id is None:
        raise ValueError("draft_id or mapping_version_id is required")

    version = await get_source_mapping_version(db, source_id, target_version_id)
    if version is None:
        raise ValueError("Mapping draft/version not found for source")

    existing_named = await db.execute(
        select(SourceMappingPreset.id).where(
            SourceMappingPreset.source_id == source_id,
            SourceMappingPreset.tenant_id == tenant_id,
            SourceMappingPreset.name == name,
        )
    )
    if existing_named.scalar_one_or_none():
        raise ValueError("Preset name already exists for this source")

    effective_statuses = include_statuses or ["approved"]
    page_types = await list_source_mapping_page_types(db, version.id)
    page_type_lookup = {page_type.id: page_type for page_type in page_types}
    rows = await list_source_mapping_rows(db, source_id, version.id, skip=0, limit=10_000)
    filtered_rows = [row for row in rows if row.status in effective_statuses]
    if not filtered_rows:
        raise ValueError("No mapping rows matched include_statuses for preset creation")

    page_type_keys = {page_type_lookup[row.page_type_id].key for row in filtered_rows if row.page_type_id in page_type_lookup}
    summary = json.dumps({"included_statuses": effective_statuses, "source_mapping_version_id": version.id})
    preset = await create_source_mapping_preset(
        db,
        source_id=source_id,
        tenant_id=tenant_id,
        name=name,
        description=description,
        created_from_mapping_version_id=version.id,
        created_by=created_by,
        row_count=len(filtered_rows),
        page_type_count=len(page_type_keys),
        summary_json=summary,
    )

    for row in filtered_rows:
        page_type = page_type_lookup.get(row.page_type_id)
        db.add(
            SourceMappingPresetRow(
                preset_id=preset.id,
                page_type_key=page_type.key if page_type else None,
                page_type_label=page_type.label if page_type else None,
                selector=row.selector,
                pattern_type=row.pattern_type,
                extraction_mode=row.extraction_mode,
                attribute_name=row.attribute_name,
                destination_entity=row.destination_entity,
                destination_field=row.destination_field,
                category_target=row.category_target,
                transforms_json=row.transforms_json,
                confidence_score=row.confidence_score,
                is_required=row.is_required,
                is_enabled=row.is_enabled,
                sort_order=row.sort_order,
                rationale_json=row.confidence_reasons_json,
            )
        )

    await db.commit()
    await db.refresh(preset)
    return preset


def has_usable_runtime_map_payload(runtime_map: dict[str, Any] | None) -> bool:
    if not isinstance(runtime_map, dict):
        return False
    crawl_plan = runtime_map.get("crawl_plan")
    has_crawl_plan = isinstance(crawl_plan, dict) and isinstance(crawl_plan.get("phases"), list) and bool(crawl_plan["phases"])
    if has_crawl_plan and has_runtime_extraction_payload(runtime_map):
        return True
    if has_crawl_plan:
        return True
    return has_runtime_extraction_payload(runtime_map)


def has_runtime_extraction_payload(runtime_map: dict[str, Any] | None) -> bool:
    if not isinstance(runtime_map, dict):
        return False
    if isinstance(runtime_map.get("mining_map"), dict) and runtime_map.get("mining_map"):
        return True
    if isinstance(runtime_map.get("extraction_rules"), dict) and runtime_map.get("extraction_rules"):
        return True
    return False


def build_runtime_map_from_preset_rows(
    preset: SourceMappingPreset,
    rows: list[SourceMappingPresetRow],
    *,
    base_runtime_map: dict[str, Any] | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    runtime_map: dict[str, Any] = dict(base_runtime_map or {})
    extraction_rules = runtime_map.get("extraction_rules")
    if not isinstance(extraction_rules, dict):
        extraction_rules = {}
        runtime_map["extraction_rules"] = extraction_rules
    page_type_rules = runtime_map.get("page_type_rules")
    if not isinstance(page_type_rules, dict):
        page_type_rules = {}
        runtime_map["page_type_rules"] = page_type_rules
    follow_rules = runtime_map.get("follow_rules")
    if not isinstance(follow_rules, dict):
        follow_rules = {}
        runtime_map["follow_rules"] = follow_rules
    asset_rules = runtime_map.get("asset_rules")
    if not isinstance(asset_rules, dict):
        asset_rules = {}
        runtime_map["asset_rules"] = asset_rules
    crawl_plan = runtime_map.get("crawl_plan")
    if not isinstance(crawl_plan, dict):
        crawl_plan = {"phases": []}
        runtime_map["crawl_plan"] = crawl_plan
    if not isinstance(crawl_plan.get("phases"), list):
        crawl_plan["phases"] = []

    page_type_seen: set[str] = set()
    for row in rows:
        if not row.is_enabled:
            continue
        page_type_key = row.page_type_key or "unknown"
        page_type_seen.add(page_type_key)
        page_rules = extraction_rules.setdefault(page_type_key, {})
        css_selectors = page_rules.setdefault("css_selectors", {})
        identifiers = page_rules.setdefault("identifiers", [])
        if not isinstance(identifiers, list):
            identifiers = []
            page_rules["identifiers"] = identifiers
        for pattern in _default_identifiers_for_page_type(page_type_key):
            if pattern not in identifiers:
                identifiers.append(pattern)
        destination_field = row.destination_field or "raw_value"
        if row.selector and destination_field not in css_selectors:
            css_selectors[destination_field] = row.selector

        type_rule = page_type_rules.setdefault(
            page_type_key,
            {
                "page_type_label": row.page_type_label or page_type_key,
                "page_role": page_type_key,
                "destination_entities": [],
                "target_record_types": [],
                "required_fields": [],
            },
        )
        if row.destination_entity and row.destination_entity not in type_rule["destination_entities"]:
            type_rule["destination_entities"].append(row.destination_entity)
        if row.destination_entity and row.destination_entity not in type_rule["target_record_types"]:
            type_rule["target_record_types"].append(row.destination_entity)
        if row.is_required and destination_field not in type_rule["required_fields"]:
            type_rule["required_fields"].append(destination_field)

        selector_l = (row.selector or "").lower()
        field_l = destination_field.lower()
        attr_l = (row.attribute_name or "").lower()
        category_l = (row.category_target or "").lower()
        extraction_mode_l = (row.extraction_mode or "").lower()
        follow = follow_rules.setdefault(page_type_key, {"selectors": [], "pagination_selectors": [], "max_depth": 1})
        if any(token in field_l for token in ("url", "link", "source_url", "ticket", "website")) or attr_l == "href":
            if row.selector not in follow["selectors"]:
                follow["selectors"].append(row.selector)
        if "pagination" in category_l or "next" in field_l or "page" in field_l:
            if row.selector not in follow["pagination_selectors"]:
                follow["pagination_selectors"].append(row.selector)

        assets = asset_rules.setdefault(page_type_key, {"selectors": [], "roles": {}})
        if any(token in field_l for token in ("image", "avatar", "thumbnail", "hero", "gallery", "logo", "document")) or extraction_mode_l in {"image", "asset"}:
            if row.selector not in assets["selectors"]:
                assets["selectors"].append(row.selector)
            role = "document" if "document" in field_l else "thumbnail" if "thumbnail" in field_l else "hero" if "hero" in field_l else "profile" if "avatar" in field_l else "gallery"
            assets["roles"][row.selector] = role
            if row.selector not in follow["selectors"] and ("href" in selector_l or attr_l == "href"):
                follow["selectors"].append(row.selector)

    synthesized_phases = _phases_for_page_types(source_url, page_type_seen)
    if synthesized_phases:
        crawl_plan["phases"] = synthesized_phases

    record_type_rules: dict[str, dict[str, Any]] = runtime_map.get("record_type_rules") if isinstance(runtime_map.get("record_type_rules"), dict) else {}
    for page_type_key, rule in page_type_rules.items():
        for record_type in rule.get("target_record_types", []) or []:
            entry = record_type_rules.setdefault(record_type, {"page_roles": [], "fields": []})
            if page_type_key not in entry["page_roles"]:
                entry["page_roles"].append(page_type_key)
            for field in (extraction_rules.get(page_type_key, {}).get("css_selectors", {}) or {}).keys():
                if field not in entry["fields"]:
                    entry["fields"].append(field)
    runtime_map["record_type_rules"] = record_type_rules

    runtime_map["runtime_map_source"] = "applied_preset"
    runtime_map["applied_preset_id"] = preset.id
    runtime_map["applied_preset_name"] = preset.name
    return runtime_map


def _default_identifiers_for_page_type(page_type_key: str) -> list[str]:
    key = (page_type_key or "").lower()
    if "event" in key:
        return ["/events/", "/event/"]
    if any(token in key for token in ("artist", "profile", "person")):
        return ["/artists/", "/people/"]
    if any(token in key for token in ("venue", "gallery", "location")):
        return ["/venues/", "/locations/", "/galleries/"]
    if "exhibition" in key:
        return ["/exhibitions/"]
    if "artwork" in key:
        return ["/artworks/", "/works/"]
    if "listing" in key or "directory" in key:
        return ["/", "/index", "/list"]
    return ["/"]


def _phase_name_for_page_type(page_type_key: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", (page_type_key or "generic").lower()).strip("_")
    return f"crawl_{normalized or 'generic'}"


def _phase_pattern_for_page_type(page_type_key: str, identifiers: list[str]) -> str:
    for identifier in identifiers:
        if isinstance(identifier, str) and identifier.strip():
            return identifier.strip()
    key = (page_type_key or "").lower()
    if "root" in key:
        return "/"
    if "directory" in key or "listing" in key:
        return "/[name]"
    return "/[name]"


def _phases_for_page_types(source_url: str | None, page_type_keys: set[str]) -> list[dict[str, Any]]:
    if not source_url:
        return []
    base = source_url.rstrip("/")
    phases: list[dict[str, Any]] = [
        {
            "phase_name": "root",
            "base_url": base,
            "url_pattern": "/",
            "pagination_type": "none",
            "num_pages": 1,
        }
    ]

    for page_type_key in sorted(page_type_keys):
        if page_type_key in {"root_page", "unknown"}:
            continue
        identifiers = _default_identifiers_for_page_type(page_type_key)
        phases.append(
            {
                "phase_name": _phase_name_for_page_type(page_type_key),
                "base_url": base,
                "url_pattern": _phase_pattern_for_page_type(page_type_key, identifiers),
                "pagination_type": "follow_links" if "detail" in page_type_key else "none",
                "num_pages": 100 if "detail" in page_type_key else 25,
                "page_role": page_type_key,
            }
        )

    return phases


async def get_active_runtime_map(
    db: AsyncSession,
    source_id: str,
) -> tuple[dict[str, Any] | None, str]:
    source = await get_source(db, source_id)
    if source is None:
        return None, "none"

    if source.structure_map:
        try:
            payload = json.loads(source.structure_map)
            if has_usable_runtime_map_payload(payload):
                runtime_source = "applied_preset" if source.active_mapping_preset_id else "source_structure_map"
                return payload, runtime_source
        except json.JSONDecodeError:
            logger.warning("source_runtime_map_invalid_json", source_id=source_id)

    return None, "none"


async def apply_source_mapping_preset_to_source(
    db: AsyncSession,
    *,
    source_id: str,
    preset_id: str,
    tenant_id: str = "public",
) -> Source:
    source = await get_source(db, source_id)
    if source is None or source.tenant_id != tenant_id:
        raise ValueError("Source not found")

    preset = await get_source_mapping_preset(db, preset_id, source_id=source_id, tenant_id=tenant_id)
    if preset is None:
        raise ValueError("Mapping preset not found for source")

    rows_result = await db.execute(
        select(SourceMappingPresetRow)
        .where(SourceMappingPresetRow.preset_id == preset.id)
        .order_by(SourceMappingPresetRow.sort_order.asc())
    )
    rows = list(rows_result.scalars().all())
    if not rows:
        raise ValueError("Mapping preset has no rows")

    base_runtime_map: dict[str, Any] | None = None
    if source.structure_map:
        try:
            parsed = json.loads(source.structure_map)
            if isinstance(parsed, dict):
                base_runtime_map = parsed
        except json.JSONDecodeError:
            base_runtime_map = None

    runtime_map = build_runtime_map_from_preset_rows(
        preset,
        rows,
        base_runtime_map=base_runtime_map,
        source_url=source.url,
    )
    source.structure_map = json.dumps(runtime_map)
    source.active_mapping_preset_id = preset.id
    source.runtime_mapping_updated_at = datetime.now(UTC)
    source.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(source)
    return source


# ---------------------------------------------------------------------------
# Page CRUD
# ---------------------------------------------------------------------------


async def create_page(db: AsyncSession, source_id: str, url: str, **kwargs: Any) -> Page:
    if "tenant_id" not in kwargs:
        source = await get_source(db, source_id)
        kwargs["tenant_id"] = source.tenant_id if source else "public"
    original_url = kwargs.pop("original_url", url)
    normalized_url = kwargs.pop("normalized_url", normalize_url(url))
    kwargs.setdefault("status", "fetched")
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    payload = {
        "source_id": source_id,
        "url": url,
        "normalized_url": normalized_url,
        "original_url": original_url,
        **kwargs,
    }
    try:
        if dialect_name == "postgresql":
            stmt = (
                pg_insert(Page)
                .values(**payload)
                .on_conflict_do_nothing(index_elements=["source_id", "normalized_url"])
                .returning(Page.id)
            )
            inserted_id = (await db.execute(stmt)).scalar_one_or_none()
            if inserted_id is not None:
                await db.commit()
                page = await get_page(db, inserted_id)
                assert page is not None
                return page
        elif dialect_name == "sqlite":
            stmt = sqlite_insert(Page).values(**payload).on_conflict_do_nothing().returning(Page.id)
            inserted_id = (await db.execute(stmt)).scalar_one_or_none()
            if inserted_id is not None:
                await db.commit()
                page = await get_page(db, inserted_id)
                assert page is not None
                return page
    except IntegrityError:
        await db.rollback()
    page = await get_page_by_normalized_url(db, source_id=source_id, normalized_url=normalized_url)
    if page is None:
        page = Page(**payload)
        db.add(page)
        await db.commit()
        await db.refresh(page)
        return page
    return page


async def get_page(db: AsyncSession, page_id: str) -> Page | None:
    result = await db.execute(select(Page).where(Page.id == page_id))
    return result.scalar_one_or_none()


async def get_or_create_page(db: AsyncSession, source_id: str, url: str) -> tuple[Page, bool]:
    normalized = normalize_url(url)
    page = await get_page_by_url(db, source_id=source_id, url=url)
    if page is not None:
        return page, False
    page = await get_page_by_normalized_url(db, source_id=source_id, normalized_url=normalized)
    if page is not None:
        return page, False
    try:
        page = await create_page(db, source_id=source_id, url=url, normalized_url=normalized)
        return page, True
    except IntegrityError:
        await db.rollback()
        page = await get_page_by_normalized_url(db, source_id=source_id, normalized_url=normalized)
        if page is None:
            raise
        return page, False


async def get_page_by_url(db: AsyncSession, *, source_id: str, url: str) -> Page | None:
    return (
        await db.execute(select(Page).where(Page.source_id == source_id, Page.url == url))
    ).scalar_one_or_none()


async def get_page_by_normalized_url(db: AsyncSession, *, source_id: str, normalized_url: str) -> Page | None:
    return (
        await db.execute(select(Page).where(Page.source_id == source_id, Page.normalized_url == normalized_url))
    ).scalar_one_or_none()


async def get_page_by_content_hash(db: AsyncSession, *, source_id: str, content_hash: str) -> Page | None:
    return (
        await db.execute(
            select(Page).where(Page.source_id == source_id, Page.content_hash == content_hash).order_by(Page.created_at.desc())
        )
    ).scalars().first()


async def list_pages(
    db: AsyncSession,
    source_id: str | None = None,
    status: str | None = None,
    page_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Page]:
    stmt = select(Page)
    if source_id:
        stmt = stmt.where(Page.source_id == source_id)
    if status:
        stmt = stmt.where(Page.status == status)
    if page_type:
        stmt = stmt.where(Page.page_type == page_type)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_pages_by_statuses(
    db: AsyncSession,
    source_id: str,
    statuses: list[str],
    *,
    limit: int = 10000,
) -> list[Page]:
    stmt: Select[tuple[Page]] = (
        select(Page)
        .where(Page.source_id == source_id, Page.status.in_(statuses))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_page(db: AsyncSession, page_id: str, **kwargs: Any) -> Page:
    page = await get_page(db, page_id)
    if page is None:
        raise ValueError(f"Page {page_id} not found")
    for key, value in kwargs.items():
        setattr(page, key, value)
    await db.commit()
    await db.refresh(page)
    return page


async def count_pages(db: AsyncSession, source_id: str, status: str | None = None) -> int:
    stmt = select(func.count(Page.id)).where(Page.source_id == source_id)
    if status:
        stmt = stmt.where(Page.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_pages_in_statuses(db: AsyncSession, source_id: str, statuses: list[str]) -> int:
    stmt = select(func.count(Page.id)).where(Page.source_id == source_id, Page.status.in_(statuses))
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_pages_by_status(db: AsyncSession, source_id: str) -> dict[str, int]:
    stmt = (
        select(Page.status, func.count(Page.id))
        .where(Page.source_id == source_id)
        .group_by(Page.status)
    )
    result = await db.execute(stmt)
    return {status: count for status, count in result.all()}


# ---------------------------------------------------------------------------
# Record CRUD
# ---------------------------------------------------------------------------


async def create_record(
    db: AsyncSession, source_id: str, record_type: str, **kwargs: Any
) -> Record:
    canonical_type = normalize_record_type(record_type)
    if "tenant_id" not in kwargs:
        source = await get_source(db, source_id)
        kwargs["tenant_id"] = source.tenant_id if source else "public"
    payload = prepare_record_payload(canonical_type, kwargs)
    kwargs["normalized_name"] = payload.normalized_name
    kwargs["fingerprint"] = payload.fingerprint
    kwargs["fingerprint_version"] = payload.fingerprint_version
    kwargs["field_confidence"] = payload.field_confidence
    kwargs["structured_data"] = payload.data.model_dump(mode="json")

    embedding_payload = _build_embedding_payload(canonical_type.value, kwargs)
    if embedding_payload is not None:
        kwargs["embedding_vector"] = embedding_payload
        kwargs["embedding_updated_at"] = datetime.now(UTC)
    if "raw_data" in kwargs:
        completeness, has_conflicts = _extract_completeness_and_conflicts(kwargs.get("raw_data"))
        kwargs.setdefault("completeness_score", completeness)
        kwargs.setdefault("has_conflicts", has_conflicts)

    existing: Record | None = None
    best_match: tuple[Record, float, str, dict[str, Any]] | None = None
    if payload.normalized_name:
        candidate_result = await db.execute(
            select(Record).where(Record.source_id == source_id, Record.record_type == canonical_type.value)
        )
        for candidate in list(candidate_result.scalars().all()):
            if not fuzzy_name_match(candidate.normalized_name or "", payload.normalized_name, threshold=0.7):
                continue
            candidate_snapshot = serialize_record_snapshot(candidate)
            score, decision, signals = classify_identity_match(
                record_type=canonical_type,
                existing_values=candidate_snapshot,
                incoming_values={"normalized_name": payload.normalized_name, **kwargs},
            )
            if best_match is None or score > best_match[1]:
                best_match = (candidate, score, decision, signals)

    match_decision: str | None = None
    review_candidate: tuple[str, float, dict[str, Any]] | None = None
    if best_match is not None:
        existing, identity_score, decision, signals = best_match
        match_decision = decision
        if decision == "review":
            kwargs.setdefault("admin_notes", f"dedup_review_required score={identity_score:.3f} signals={signals}")
            review_candidate = (existing.id, identity_score, signals)
            existing = None
        elif decision == "new":
            existing = None

    if existing is not None:
        existing_snapshot = serialize_record_snapshot(existing)
        raw_payload: dict[str, Any] = {}
        if isinstance(existing.raw_data, str):
            try:
                parsed = json.loads(existing.raw_data)
                if isinstance(parsed, dict):
                    raw_payload = parsed
            except json.JSONDecodeError:
                raw_payload = {}
        merged_values, changes = merge_record(existing_snapshot, kwargs)
        raw_payload["field_provenance"] = merged_values.get("field_provenance", {})
        raw_payload["conflicts"] = merged_values.get("conflicts", {})
        raw_payload["merge_events"] = raw_payload.get("merge_events", [])
        raw_payload["merge_events"].append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "involved_record_ids": [existing.id, f"incoming:{payload.fingerprint}"],
                "before": existing_snapshot,
                "after": {**existing_snapshot, **{k: v.get("after") for k, v in changes.items()}},
                "changes": changes,
            }
        )
        merged_values["raw_data"] = json.dumps(raw_payload, default=str)
        merged_values.pop("id", None)
        merged_values.pop("source_id", None)
        merged_values.pop("record_type", None)
        merged_values.pop("created_at", None)
        merged_values.pop("updated_at", None)
        for key, value in merged_values.items():
            if hasattr(existing, key):
                if key in {"artist_names", "mediums", "collections", "confidence_reasons"} and isinstance(value, list):
                    value = json.dumps(value)
                setattr(existing, key, value)
        existing.updated_at = datetime.now(UTC)
        db.add(
            MergeHistory(
                primary_record_id=existing.id,
                secondary_record_id=f"incoming:{payload.fingerprint}",
                source_id=source_id,
                primary_snapshot=build_merge_snapshot(existing_snapshot, kwargs, changes),
                secondary_snapshot=json.dumps(kwargs, default=str),
                relationships_snapshot=json.dumps([]),
            )
        )
        await db.commit()
        await db.refresh(existing)
        return existing

    if payload.normalized_name and match_decision in {"review", "new"}:
        name_collision = await db.execute(
            select(func.count(Record.id)).where(
                Record.source_id == source_id,
                Record.record_type == canonical_type.value,
                Record.normalized_name == payload.normalized_name,
            )
        )
        if int(name_collision.scalar_one() or 0) > 0:
            kwargs["normalized_name"] = f"{payload.normalized_name}--{payload.fingerprint[:12]}"

    insert_values = dict(kwargs)
    for field in ("artist_names", "mediums", "collections", "confidence_reasons"):
        if field in insert_values and isinstance(insert_values[field], list):
            insert_values[field] = json.dumps(insert_values[field])
    record = Record(source_id=source_id, record_type=canonical_type.value, **insert_values)
    db.add(record)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(Record).where(
                Record.source_id == source_id,
                Record.record_type == canonical_type.value,
                Record.normalized_name == payload.normalized_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise
        return existing
    await db.refresh(record)
    if review_candidate is not None:
        left_record_id, identity_score, signals = review_candidate
        await upsert_duplicate_review(
            db,
            left_record_id=left_record_id,
            right_record_id=record.id,
            similarity_score=int(round(identity_score * 100)),
            reason=f"dedup review required: {json.dumps(signals, default=str)}",
            needs_review=True,
        )
    return record


async def get_record_by_page_and_type(
    db: AsyncSession,
    *,
    source_id: str,
    page_id: str,
    record_type: str,
) -> Record | None:
    result = await db.execute(
        select(Record).where(
            Record.source_id == source_id,
            Record.page_id == page_id,
            Record.record_type == normalize_record_type(record_type).value,
        )
    )
    return result.scalar_one_or_none()


async def get_artist_record_by_family_key(
    db: AsyncSession,
    *,
    source_id: str,
    family_key: str,
) -> Record | None:
    result = await db.execute(
        select(Record).where(
            Record.source_id == source_id,
            Record.record_type == normalize_record_type("artist").value,
            Record.raw_data.is_not(None),
            Record.raw_data.contains(f'"artist_family_key": "{family_key}"'),
        )
    )
    return result.scalars().first()


async def get_record_by_item_fingerprint(
    db: AsyncSession,
    *,
    source_id: str,
    page_id: str | None,
    record_type: str,
    item_fingerprint: str,
) -> Record | None:
    stmt = select(Record).where(
        Record.source_id == source_id,
        Record.record_type == normalize_record_type(record_type).value,
        Record.raw_data.is_not(None),
        Record.raw_data.contains(f'"item_fingerprint": "{item_fingerprint}"'),
    )
    if page_id is not None:
        stmt = stmt.where(Record.page_id == page_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_record(db: AsyncSession, record_id: str) -> Record | None:
    result = await db.execute(select(Record).where(Record.id == record_id))
    return result.scalar_one_or_none()


async def list_records(
    db: AsyncSession,
    tenant_id: str | None = None,
    source_id: str | None = None,
    record_type: str | None = None,
    status: str | None = None,
    confidence_band: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Record]:
    stmt = select(Record)
    if tenant_id:
        stmt = stmt.where(Record.tenant_id == tenant_id)
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    if record_type:
        stmt = stmt.where(Record.record_type == normalize_record_type(record_type).value)
    if status:
        stmt = stmt.where(Record.status == status)
    if confidence_band:
        stmt = stmt.where(Record.confidence_band == confidence_band)
    if search:
        stmt = stmt.where(Record.title.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def search_records(
    db: AsyncSession,
    *,
    record_type: str,
    query: str | None = None,
    location: str | None = None,
    min_completeness_score: int | None = None,
    has_exhibitions: bool | None = None,
    has_articles: bool | None = None,
    has_conflicts: bool | None = None,
    sort_by: str = "completeness",
    skip: int = 0,
    limit: int = 50,
) -> list[Record]:
    stmt = select(Record).where(Record.record_type == normalize_record_type(record_type).value)
    if query:
        query_filter = f"%{query}%"
        stmt = stmt.where(
            or_(
                Record.title.ilike(query_filter),
                Record.description.ilike(query_filter),
                Record.bio.ilike(query_filter),
            )
        )
    if location:
        location_filter = f"%{location}%"
        stmt = stmt.where(
            or_(
                Record.city.ilike(location_filter),
                Record.country.ilike(location_filter),
                Record.venue_name.ilike(location_filter),
                Record.venue_address.ilike(location_filter),
                Record.nationality.ilike(location_filter),
            )
        )
    if min_completeness_score is not None:
        stmt = stmt.where(Record.completeness_score >= min_completeness_score)
    if has_conflicts is not None:
        stmt = stmt.where(Record.has_conflicts.is_(has_conflicts))
    if has_exhibitions is not None:
        comparator = Record.raw_data.contains('"exhibitions"')
        stmt = stmt.where(comparator if has_exhibitions else ~comparator)
    if has_articles is not None:
        comparator = Record.raw_data.contains('"articles"')
        stmt = stmt.where(comparator if has_articles else ~comparator)

    if sort_by == "alphabetical":
        stmt = stmt.order_by(Record.title.asc().nullslast())
    elif sort_by == "number_of_exhibitions":
        stmt = stmt.order_by(Record.raw_data.desc().nullslast())
    else:
        stmt = stmt.order_by(Record.completeness_score.desc(), Record.title.asc().nullslast())

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_search_records(
    db: AsyncSession,
    *,
    record_type: str,
    query: str | None = None,
    location: str | None = None,
    min_completeness_score: int | None = None,
    has_exhibitions: bool | None = None,
    has_articles: bool | None = None,
    has_conflicts: bool | None = None,
) -> int:
    stmt = select(func.count(Record.id)).where(Record.record_type == normalize_record_type(record_type).value)
    if query:
        query_filter = f"%{query}%"
        stmt = stmt.where(
            or_(
                Record.title.ilike(query_filter),
                Record.description.ilike(query_filter),
                Record.bio.ilike(query_filter),
            )
        )
    if location:
        location_filter = f"%{location}%"
        stmt = stmt.where(
            or_(
                Record.city.ilike(location_filter),
                Record.country.ilike(location_filter),
                Record.venue_name.ilike(location_filter),
                Record.venue_address.ilike(location_filter),
                Record.nationality.ilike(location_filter),
            )
        )
    if min_completeness_score is not None:
        stmt = stmt.where(Record.completeness_score >= min_completeness_score)
    if has_conflicts is not None:
        stmt = stmt.where(Record.has_conflicts.is_(has_conflicts))
    if has_exhibitions is not None:
        comparator = Record.raw_data.contains('"exhibitions"')
        stmt = stmt.where(comparator if has_exhibitions else ~comparator)
    if has_articles is not None:
        comparator = Record.raw_data.contains('"articles"')
        stmt = stmt.where(comparator if has_articles else ~comparator)
    result = await db.execute(stmt)
    return result.scalar_one()


async def update_record(db: AsyncSession, record_id: str, **kwargs: Any) -> Record:
    record = await get_record(db, record_id)
    if record is None:
        raise ValueError(f"Record {record_id} not found")
    updated_values: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in ("artist_names", "mediums", "collections", "confidence_reasons") and isinstance(
            value, list
        ):
            value = json.dumps(value)
        setattr(record, key, value)
        updated_values[key] = value
    payload = prepare_record_payload(record.record_type, {**record.__dict__, **updated_values})
    record.normalized_name = payload.normalized_name
    record.fingerprint = payload.fingerprint
    record.field_confidence = payload.field_confidence
    record.structured_data = payload.data.model_dump(mode="json")
    embedding_payload = _build_embedding_payload(record.record_type, {**record.__dict__, **updated_values})
    if embedding_payload is not None:
        record.embedding_vector = embedding_payload
        record.embedding_updated_at = datetime.now(UTC)
    if "raw_data" in kwargs:
        completeness, has_conflicts = _extract_completeness_and_conflicts(record.raw_data)
        record.completeness_score = completeness
        record.has_conflicts = has_conflicts
    record.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record


async def approve_record(db: AsyncSession, record_id: str) -> Record:
    return await update_record(db, record_id, status="approved")


async def reject_record(db: AsyncSession, record_id: str) -> Record:
    return await update_record(db, record_id, status="rejected")


async def bulk_approve(db: AsyncSession, source_id: str, min_confidence: int = 70) -> int:
    result = await db.execute(
        select(Record).where(
            Record.source_id == source_id,
            Record.status == "pending",
            Record.confidence_score >= min_confidence,
        )
    )
    records = list(result.scalars().all())
    for record in records:
        record.status = "approved"
        record.updated_at = datetime.now(UTC)
    await db.commit()
    return len(records)


async def count_records(
    db: AsyncSession,
    tenant_id: str | None = None,
    source_id: str | None = None,
    status: str | None = None,
    record_type: str | None = None,
    search: str | None = None,
) -> int:
    stmt = select(func.count(Record.id))
    if tenant_id:
        stmt = stmt.where(Record.tenant_id == tenant_id)
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    if status:
        stmt = stmt.where(Record.status == status)
    if record_type:
        stmt = stmt.where(Record.record_type == normalize_record_type(record_type).value)
    if search:
        query_filter = f"%{search}%"
        stmt = stmt.where(
            or_(
                Record.title.ilike(query_filter),
                Record.description.ilike(query_filter),
                Record.bio.ilike(query_filter),
            )
        )
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_records_by_type(db: AsyncSession, source_id: str) -> dict[str, int]:
    stmt = (
        select(Record.record_type, func.count(Record.id))
        .where(Record.source_id == source_id)
        .group_by(Record.record_type)
    )
    result = await db.execute(stmt)
    return {record_type: count for record_type, count in result.all()}


# ---------------------------------------------------------------------------
# Image CRUD
# ---------------------------------------------------------------------------


async def create_image(db: AsyncSession, source_id: str, url: str, **kwargs: Any) -> Image:
    if "tenant_id" not in kwargs:
        source = await get_source(db, source_id)
        kwargs["tenant_id"] = source.tenant_id if source else "public"
    image_hash = kwargs.get("image_hash") or hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()
    kwargs["image_hash"] = image_hash
    existing_result = await db.execute(
        select(Image).where(
            Image.source_id == source_id,
            Image.image_hash == image_hash,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        incoming_record_id = kwargs.get("record_id")
        incoming_confidence = int(kwargs.get("confidence", 0) or 0)
        allow_reassign = bool(kwargs.pop("allow_reassign", False))
        if incoming_record_id and (
            existing.record_id is None
            or existing.record_id == incoming_record_id
            or allow_reassign
            or incoming_confidence > int(existing.confidence or 0)
        ):
            existing.record_id = incoming_record_id
            existing.page_id = kwargs.get("page_id", existing.page_id)
            existing.confidence = max(int(existing.confidence or 0), incoming_confidence)
            await db.commit()
            await db.refresh(existing)
        return existing
    image = Image(source_id=source_id, url=url, **kwargs)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def list_images(
    db: AsyncSession,
    record_id: str | None = None,
    source_id: str | None = None,
    image_type: str | None = None,
    is_valid: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Image]:
    stmt = select(Image)
    if record_id:
        stmt = stmt.where(Image.record_id == record_id)
    if source_id:
        stmt = stmt.where(Image.source_id == source_id)
    if image_type:
        stmt = stmt.where(Image.image_type == image_type)
    if is_valid is not None:
        stmt = stmt.where(Image.is_valid == is_valid)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_images(db: AsyncSession, source_id: str | None = None, record_id: str | None = None) -> int:
    stmt = select(func.count(Image.id))
    if source_id:
        stmt = stmt.where(Image.source_id == source_id)
    if record_id:
        stmt = stmt.where(Image.record_id == record_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def set_primary_image(db: AsyncSession, record_id: str, image_id: str) -> Record:
    record = await get_record(db, record_id)
    if record is None:
        raise ValueError(f"Record {record_id} not found")
    record.primary_image_id = image_id
    record.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------


async def create_job(
    db: AsyncSession, source_id: str, job_type: str, payload: dict[str, Any]
) -> Job:
    source = await get_source(db, source_id)
    job = Job(
        source_id=source_id,
        tenant_id=source.tenant_id if source else "public",
        job_type=job_type,
        payload=json.dumps(payload),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def wait_for_job(
    db: AsyncSession,
    job_id: str,
    *,
    retries: int = 3,
    delay_seconds: float = 0.2,
) -> Job | None:
    """Wait briefly for job visibility across transactions/processes."""
    for attempt in range(retries):
        job = await get_job(db, job_id)
        if job is not None:
            return job
        if attempt < retries - 1:
            await sleep(delay_seconds)
    return None


async def get_next_pending_job(db: AsyncSession) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.status == "pending").order_by(Job.created_at).limit(1)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession, job_id: str, status: str, **kwargs: Any
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    job.status = status
    for key, value in kwargs.items():
        if key == "result" and isinstance(value, dict):
            value = json.dumps(value)
        setattr(job, key, value)
    await db.commit()
    await db.refresh(job)
    return job


async def claim_job_for_worker(
    db: AsyncSession,
    *,
    job_id: str,
    worker_id: str,
    max_concurrent_jobs: int,
) -> Job | None:
    running_count = (
        await db.execute(select(func.count(Job.id)).where(Job.status == "running"))
    ).scalar_one()
    if int(running_count or 0) >= max_concurrent_jobs:
        return None

    job = await get_job(db, job_id)
    if job is None:
        return None
    if job.status in TERMINAL_JOB_STATUSES | {"paused"}:
        return None

    job.status = "running"
    job.worker_id = worker_id
    if job.started_at is None:
        job.started_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(job)
    return job


async def list_jobs(
    db: AsyncSession,
    source_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Job]:
    stmt = select(Job)
    if source_id:
        stmt = stmt.where(Job.source_id == source_id)
    if status:
        stmt = stmt.where(Job.status == status)
    stmt = stmt.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_job_progress(
    db: AsyncSession,
    job_id: str,
    *,
    stage: str | None = None,
    item: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    last_log_message: str | None = None,
    metrics: dict[str, Any] | None = None,
    heartbeat: bool = True,
    worker_id: str | None = None,
) -> Job | None:
    job = await get_job(db, job_id)
    if job is None:
        return None

    if stage is not None:
        job.current_stage = stage
    if item is not None:
        job.current_item = item
    if progress_current is not None:
        job.progress_current = progress_current
    if progress_total is not None:
        job.progress_total = progress_total
    if last_log_message is not None:
        job.last_log_message = last_log_message
    if metrics is not None:
        job.metrics_json = json.dumps(metrics)
    if heartbeat:
        job.last_heartbeat_at = datetime.now(UTC)
    if worker_id is not None:
        job.worker_id = worker_id

    await db.commit()
    await db.refresh(job)
    return job


async def append_job_event(
    db: AsyncSession,
    *,
    job_id: str,
    source_id: str | None,
    worker_id: str | None = None,
    event_type: str,
    message: str,
    level: str = "info",
    stage: str | None = None,
    context: dict[str, Any] | None = None,
) -> JobEvent:
    job = await get_job(db, job_id)
    tenant_id = job.tenant_id if job else "public"
    event = JobEvent(
        tenant_id=tenant_id,
        job_id=job_id,
        source_id=source_id,
        worker_id=worker_id,
        event_type=event_type,
        message=message,
        level=level,
        stage=stage,
        context=json.dumps(context, default=str) if context is not None else None,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_job_events(
    db: AsyncSession,
    job_id: str,
    *,
    limit: int = 100,
    before: datetime | None = None,
) -> list[JobEvent]:
    stmt = select(JobEvent).where(JobEvent.job_id == job_id)
    if before is not None:
        stmt = stmt.where(JobEvent.timestamp < before)
    stmt = stmt.order_by(JobEvent.timestamp.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


async def upsert_worker_state(
    db: AsyncSession,
    *,
    worker_id: str,
    status: str,
    current_job_id: str | None = None,
    current_stage: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> WorkerState:
    worker = await db.get(WorkerState, worker_id)
    if worker is None:
        worker = WorkerState(worker_id=worker_id)
        db.add(worker)

    worker.status = status
    worker.current_job_id = current_job_id
    worker.current_stage = current_stage
    worker.last_heartbeat_at = datetime.now(UTC)
    if metrics is not None:
        worker.metrics_json = json.dumps(metrics, default=str)
    await db.commit()
    await db.refresh(worker)
    return worker


async def heartbeat_worker(
    db: AsyncSession,
    *,
    worker_id: str,
    status: str,
    current_job_id: str | None = None,
    current_stage: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> WorkerState:
    return await upsert_worker_state(
        db,
        worker_id=worker_id,
        status=status,
        current_job_id=current_job_id,
        current_stage=current_stage,
        metrics=metrics,
    )


async def list_worker_states(db: AsyncSession) -> list[WorkerState]:
    rows = (await db.execute(select(WorkerState).order_by(WorkerState.worker_id.asc()))).scalars().all()
    return list(rows)


async def list_pages_for_artist_family(
    db: AsyncSession,
    *,
    source_id: str,
    family_key: str,
) -> list[Page]:
    _, slug = family_key.split("::", 1)
    stmt = select(Page).where(
        Page.source_id == source_id,
        Page.url.contains(f"/{slug}"),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_artist_records(
    db: AsyncSession,
    *,
    source_id: str | None = None,
    limit: int = 1000,
) -> list[Record]:
    stmt = select(Record).where(Record.record_type == "artist").limit(limit)
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_records_for_artist_family(
    db: AsyncSession,
    *,
    source_id: str,
    page_ids: list[str],
) -> list[Record]:
    if not page_ids:
        return []
    stmt = select(Record).where(
        Record.source_id == source_id,
        Record.page_id.in_(page_ids),
        Record.record_type.in_(["exhibition", "artist_article", "artist_press", "artist_memory"]),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def parse_embedding(embedding_value: Any) -> list[float]:
    if embedding_value is None:
        return []
    if isinstance(embedding_value, str):
        try:
            parsed = json.loads(embedding_value)
        except (TypeError, json.JSONDecodeError):
            return []
    elif isinstance(embedding_value, (list, tuple)):
        parsed = list(embedding_value)
    else:
        return []
    if not isinstance(parsed, list):
        return []
    vector: list[float] = []
    for item in parsed:
        try:
            value = float(item)
        except (TypeError, ValueError):
            return []
        if math.isnan(value) or math.isinf(value):
            return []
        vector.append(value)
    return vector


def embedding_similarity(left: Record, right: Record) -> float:
    return cosine_similarity(parse_embedding(left.embedding_vector), parse_embedding(right.embedding_vector))


async def upsert_entity_relationship(
    db: AsyncSession,
    *,
    source_id: str,
    from_record_id: str,
    to_record_id: str,
    relationship_type: str,
    metadata: dict[str, Any] | None = None,
) -> EntityRelationship:
    stmt = select(EntityRelationship).where(
        EntityRelationship.source_id == source_id,
        EntityRelationship.from_record_id == from_record_id,
        EntityRelationship.to_record_id == to_record_id,
        EntityRelationship.relationship_type == relationship_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        if metadata is not None:
            existing.metadata_json = json.dumps(metadata)
        await db.commit()
        await db.refresh(existing)
        return existing

    rel = EntityRelationship(
        source_id=source_id,
        from_record_id=from_record_id,
        to_record_id=to_record_id,
        relationship_type=relationship_type,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


async def ensure_entity_relationship(
    db: AsyncSession,
    *,
    source_id: str,
    from_record_id: str,
    to_record_id: str,
    relationship_type: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    stmt = select(EntityRelationship).where(
        EntityRelationship.source_id == source_id,
        EntityRelationship.from_record_id == from_record_id,
        EntityRelationship.to_record_id == to_record_id,
        EntityRelationship.relationship_type == relationship_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return False
    rel = EntityRelationship(
        source_id=source_id,
        from_record_id=from_record_id,
        to_record_id=to_record_id,
        relationship_type=relationship_type,
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(rel)
    await db.commit()
    return True


async def list_relationships_for_record(
    db: AsyncSession,
    *,
    source_id: str | None,
    record_id: str,
    tenant_id: str | None = None,
) -> list[EntityRelationship]:
    stmt = select(EntityRelationship).where(
        or_(
            EntityRelationship.from_record_id == record_id,
            EntityRelationship.to_record_id == record_id,
        ),
    )
    if source_id:
        stmt = stmt.where(EntityRelationship.source_id == source_id)
    if tenant_id:
        stmt = stmt.where(
            EntityRelationship.source_id.in_(
                select(Source.id).where(Source.tenant_id == tenant_id)
            )
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_entities(
    db: AsyncSession,
    *,
    entity_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Entity]:
    stmt = select(Entity).order_by(Entity.updated_at.desc())
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def count_entities(db: AsyncSession, *, entity_type: str | None = None) -> int:
    stmt = select(func.count(Entity.id))
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def get_entity(db: AsyncSession, entity_id: str) -> Entity | None:
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    return result.scalar_one_or_none()


async def get_entity_link_for_record(db: AsyncSession, record_id: str) -> EntityLink | None:
    result = await db.execute(select(EntityLink).where(EntityLink.record_id == record_id))
    return result.scalar_one_or_none()


async def list_records_for_entity(db: AsyncSession, entity_id: str) -> list[Record]:
    stmt = (
        select(Record)
        .join(EntityLink, EntityLink.record_id == Record.id)
        .where(EntityLink.entity_id == entity_id)
        .order_by(Record.updated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_relationships_for_entity(db: AsyncSession, entity_id: str) -> list[EntityRelationship]:
    stmt = select(EntityRelationship).where(
        or_(
            EntityRelationship.from_entity_id == entity_id,
            EntityRelationship.to_entity_id == entity_id,
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_entity_conflicts(db: AsyncSession, *, limit: int = 100) -> list[dict[str, Any]]:
    stmt = select(Entity).order_by(Entity.updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    conflicts: list[dict[str, Any]] = []
    for entity in result.scalars().all():
        canonical_data = entity.canonical_data or {}
        items = canonical_data.get("conflicts", [])
        if not isinstance(items, list) or not items:
            continue
        conflicts.append(
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "canonical_name": entity.canonical_name,
                "conflicts": items,
            }
        )
    return conflicts


async def upsert_duplicate_review(
    db: AsyncSession,
    *,
    left_record_id: str,
    right_record_id: str,
    similarity_score: int,
    reason: str,
    needs_review: bool = False,
) -> DuplicateReview:
    left_id, right_id = _ordered_pair(left_record_id, right_record_id)
    stmt = select(DuplicateReview).where(
        DuplicateReview.left_record_id == left_id,
        DuplicateReview.right_record_id == right_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        existing.similarity_score = similarity_score
        existing.reason = reason
        existing.needs_review = needs_review
        await db.commit()
        await db.refresh(existing)
        return existing

    review = DuplicateReview(
        left_record_id=left_id,
        right_record_id=right_id,
        similarity_score=similarity_score,
        needs_review=needs_review,
        reason=reason,
        status="pending",
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def list_duplicate_reviews(
    db: AsyncSession,
    *,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[DuplicateReview]:
    stmt = select(DuplicateReview).order_by(DuplicateReview.similarity_score.desc(), DuplicateReview.created_at.desc())
    if status:
        stmt = stmt.where(DuplicateReview.status == status)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_duplicate_reviews(db: AsyncSession, *, status: str | None = None) -> int:
    stmt = select(func.count(DuplicateReview.id))
    if status:
        stmt = stmt.where(DuplicateReview.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_duplicate_review_by_pair(
    db: AsyncSession,
    *,
    left_record_id: str,
    right_record_id: str,
) -> DuplicateReview | None:
    left_id, right_id = _ordered_pair(left_record_id, right_record_id)
    stmt = select(DuplicateReview).where(
        DuplicateReview.left_record_id == left_id,
        DuplicateReview.right_record_id == right_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def set_duplicate_review_status(
    db: AsyncSession,
    *,
    review_id: str,
    status: str,
    reviewed_by: str | None = None,
    merge_target_id: str | None = None,
) -> DuplicateReview:
    stmt = select(DuplicateReview).where(DuplicateReview.id == review_id)
    review = (await db.execute(stmt)).scalar_one_or_none()
    if review is None:
        raise ValueError(f"Duplicate review {review_id} not found")
    review.status = status
    review.reviewed_by = reviewed_by
    review.reviewed_at = datetime.now(UTC)
    review.merge_target_id = merge_target_id
    await db.commit()
    await db.refresh(review)
    return review


async def get_duplicate_review(
    db: AsyncSession,
    review_id: str,
) -> DuplicateReview | None:
    stmt = select(DuplicateReview).where(DuplicateReview.id == review_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_duplicate_reviews_for_source(
    db: AsyncSession,
    *,
    source_id: str,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[DuplicateReview]:
    left_record = aliased(Record)
    right_record = aliased(Record)
    stmt = (
        select(DuplicateReview)
        .join(left_record, DuplicateReview.left_record_id == left_record.id)
        .join(right_record, DuplicateReview.right_record_id == right_record.id)
        .where(or_(left_record.source_id == source_id, right_record.source_id == source_id))
    )
    if status:
        stmt = stmt.where(DuplicateReview.status == status)
    stmt = stmt.order_by(DuplicateReview.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


async def create_audit_action(
    db: AsyncSession,
    *,
    action_type: str,
    user_id: str | None = None,
    source_id: str | None = None,
    record_id: str | None = None,
    affected_record_ids: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> AuditAction:
    action = AuditAction(
        action_type=action_type,
        user_id=user_id,
        source_id=source_id,
        record_id=record_id,
        affected_record_ids=json.dumps(affected_record_ids or []),
        details_json=json.dumps(details) if details is not None else None,
    )
    db.add(action)
    db.add(
        AuditEvent(
            event_type=action_type,
            entity_type="record" if record_id else ("source" if source_id else "system"),
            entity_id=record_id or source_id or action.id,
            user_id=user_id,
            user_name=user_id,
            source_id=source_id,
            record_id=record_id,
            message=f"Audit action: {action_type}",
            metadata_json=json.dumps(details or {}),
            changes_json=None,
        )
    )
    await db.commit()
    await db.refresh(action)
    return action


async def list_audit_actions(
    db: AsyncSession,
    *,
    action_type: str | None = None,
    source_id: str | None = None,
    record_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditAction]:
    stmt = select(AuditAction).order_by(AuditAction.created_at.desc())
    if action_type:
        stmt = stmt.where(AuditAction.action_type == action_type)
    if source_id:
        stmt = stmt.where(AuditAction.source_id == source_id)
    if record_id:
        stmt = stmt.where(AuditAction.record_id == record_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_audit_actions(db: AsyncSession, *, action_type: str | None = None) -> int:
    stmt = select(func.count(AuditAction.id))
    if action_type:
        stmt = stmt.where(AuditAction.action_type == action_type)
    result = await db.execute(stmt)
    return result.scalar_one()


async def create_audit_event(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: str | None = None,
    user_name: str | None = None,
    source_id: str | None = None,
    record_id: str | None = None,
    message: str | None = None,
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        user_name=user_name,
        source_id=source_id,
        record_id=record_id,
        message=message,
        changes_json=json.dumps(changes) if changes is not None else None,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_audit_event(db: AsyncSession, event_id: str) -> AuditEvent | None:
    stmt = select(AuditEvent).where(AuditEvent.id == event_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_audit_events(
    db: AsyncSession,
    *,
    event_type: str | None = None,
    entity_type: str | None = None,
    user_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if user_id:
        stmt = stmt.where(AuditEvent.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditEvent.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditEvent.created_at <= date_to)
    if search:
        wildcard = f"%{search}%"
        stmt = stmt.where(
            or_(
                AuditEvent.message.ilike(wildcard),
                AuditEvent.entity_id.ilike(wildcard),
                AuditEvent.user_id.ilike(wildcard),
                AuditEvent.user_name.ilike(wildcard),
            )
        )
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def count_audit_events(
    db: AsyncSession,
    *,
    event_type: str | None = None,
    entity_type: str | None = None,
    user_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
) -> int:
    stmt = select(func.count(AuditEvent.id))
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if user_id:
        stmt = stmt.where(AuditEvent.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditEvent.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditEvent.created_at <= date_to)
    if search:
        wildcard = f"%{search}%"
        stmt = stmt.where(
            or_(
                AuditEvent.message.ilike(wildcard),
                AuditEvent.entity_id.ilike(wildcard),
                AuditEvent.user_id.ilike(wildcard),
                AuditEvent.user_name.ilike(wildcard),
            )
        )
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def create_scheduled_job(
    db: AsyncSession,
    *,
    source_id: str | None,
    job_type: str,
    cron_expr: str,
    payload: dict[str, Any] | None = None,
    enabled: bool = True,
) -> ScheduledJob:
    scheduled = ScheduledJob(
        source_id=source_id,
        job_type=job_type,
        cron_expr=cron_expr,
        payload=json.dumps(payload or {}),
        enabled=enabled,
    )
    db.add(scheduled)
    await db.commit()
    await db.refresh(scheduled)
    return scheduled


async def list_scheduled_jobs(db: AsyncSession, *, source_id: str | None = None) -> list[ScheduledJob]:
    stmt = select(ScheduledJob).order_by(ScheduledJob.created_at.desc())
    if source_id:
        stmt = stmt.where(ScheduledJob.source_id == source_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert_metric_snapshot(
    db: AsyncSession,
    *,
    bucket_date: str,
    metrics: dict[str, Any],
) -> MetricSnapshot:
    existing = (
        await db.execute(select(MetricSnapshot).where(MetricSnapshot.bucket_date == bucket_date))
    ).scalar_one_or_none()
    if existing:
        existing.metrics_json = json.dumps(metrics)
        await db.commit()
        await db.refresh(existing)
        return existing

    snapshot = MetricSnapshot(bucket_date=bucket_date, metrics_json=json.dumps(metrics))
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def list_metric_snapshots(
    db: AsyncSession,
    *,
    since_date: str | None = None,
    limit: int = 30,
) -> list[MetricSnapshot]:
    stmt = select(MetricSnapshot).order_by(MetricSnapshot.bucket_date.desc())
    if since_date:
        stmt = stmt.where(MetricSnapshot.bucket_date >= since_date)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_merge_history(
    db: AsyncSession,
    *,
    primary_record: Record,
    secondary_record: Record,
    relationships_snapshot: list[dict[str, Any]],
) -> MergeHistory:
    history = MergeHistory(
        primary_record_id=primary_record.id,
        secondary_record_id=secondary_record.id,
        source_id=primary_record.source_id,
        primary_snapshot=json.dumps(serialize_record_snapshot(primary_record)),
        secondary_snapshot=json.dumps(serialize_record_snapshot(secondary_record)),
        relationships_snapshot=json.dumps(relationships_snapshot),
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


async def get_merge_history(db: AsyncSession, merge_id: str) -> MergeHistory | None:
    return (await db.execute(select(MergeHistory).where(MergeHistory.id == merge_id))).scalar_one_or_none()


async def mark_merge_history_rolled_back(db: AsyncSession, merge_id: str) -> MergeHistory:
    history = await get_merge_history(db, merge_id)
    if history is None:
        raise ValueError("Merge history not found")
    history.rolled_back = True
    history.rollback_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(history)
    return history


# ---------------------------------------------------------------------------
# Tenant / API Key / Usage
# ---------------------------------------------------------------------------


async def ensure_tenant(
    db: AsyncSession,
    tenant_id: str,
    *,
    name: str | None = None,
) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant:
        return tenant
    tenant = Tenant(id=tenant_id, name=name or tenant_id)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def create_api_key(
    db: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    key_prefix: str,
    key_hash: str,
    permissions_json: str = '["read"]',
) -> APIKey:
    key = APIKey(
        tenant_id=tenant_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        permissions_json=permissions_json,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> APIKey | None:
    return (
        await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    ).scalar_one_or_none()


async def list_api_keys(db: AsyncSession, *, tenant_id: str | None = None) -> list[APIKey]:
    stmt = select(APIKey).order_by(APIKey.created_at.desc())
    if tenant_id:
        stmt = stmt.where(APIKey.tenant_id == tenant_id)
    return list((await db.execute(stmt)).scalars().all())


async def disable_api_key(db: AsyncSession, *, key_id: str, tenant_id: str | None = None) -> bool:
    stmt = select(APIKey).where(APIKey.id == key_id)
    if tenant_id:
        stmt = stmt.where(APIKey.tenant_id == tenant_id)
    key = (await db.execute(stmt)).scalar_one_or_none()
    if key is None:
        return False
    key.enabled = False
    key.disabled_at = datetime.now(UTC)
    await db.commit()
    return True


async def touch_api_key(db: AsyncSession, key: APIKey) -> None:
    key.usage_count = int(key.usage_count or 0) + 1
    key.last_used_at = datetime.now(UTC)
    await db.commit()


async def create_api_usage_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    api_key_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
) -> APIUsageEvent:
    usage = APIUsageEvent(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
    )
    db.add(usage)
    await db.commit()
    await db.refresh(usage)
    return usage


async def get_usage_summary(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    api_key_id: str | None = None,
) -> dict[str, Any]:
    filters = []
    if tenant_id:
        filters.append(APIUsageEvent.tenant_id == tenant_id)
    if api_key_id:
        filters.append(APIUsageEvent.api_key_id == api_key_id)

    total = (
        await db.execute(select(func.count(APIUsageEvent.id)).where(*filters))
    ).scalar_one()
    avg_ms = (
        await db.execute(select(func.avg(APIUsageEvent.response_time_ms)).where(*filters))
    ).scalar_one_or_none()

    endpoints_stmt = (
        select(APIUsageEvent.endpoint, func.count(APIUsageEvent.id))
        .where(*filters)
        .group_by(APIUsageEvent.endpoint)
        .order_by(func.count(APIUsageEvent.id).desc())
    )
    endpoint_rows = (await db.execute(endpoints_stmt)).all()
    return {
        "total_requests": int(total or 0),
        "avg_response_time_ms": float(avg_ms or 0),
        "endpoint_usage": [{"endpoint": row[0], "count": row[1]} for row in endpoint_rows],
    }


async def create_crawl_run(
    db: AsyncSession,
    *,
    source_id: str,
    seed_url: str,
    job_id: str | None = None,
    status: str = "queued",
    worker_id: str | None = None,
    mapping_version_id: str | None = None,
) -> CrawlRun:
    crawl_run = CrawlRun(
        source_id=source_id,
        job_id=job_id,
        seed_url=seed_url,
        status=status,
        worker_id=worker_id,
        mapping_version_id=mapping_version_id,
        started_at=datetime.now(UTC) if status == "running" else None,
    )
    db.add(crawl_run)
    await db.commit()
    await db.refresh(crawl_run)
    return crawl_run


async def get_crawl_run(db: AsyncSession, crawl_run_id: str) -> CrawlRun | None:
    return (await db.execute(select(CrawlRun).where(CrawlRun.id == crawl_run_id))).scalar_one_or_none()


async def list_crawl_runs(db: AsyncSession, source_id: str, limit: int = 20) -> list[CrawlRun]:
    stmt = select(CrawlRun).where(CrawlRun.source_id == source_id).order_by(CrawlRun.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def get_active_crawl_run_for_source(db: AsyncSession, source_id: str) -> CrawlRun | None:
    """Return the latest non-cancelled crawl run, preferring active statuses."""
    active_stmt = (
        select(CrawlRun)
        .where(
            CrawlRun.source_id == source_id,
            CrawlRun.status.in_(["queued", "running", "paused", "cooling_down", "stale"]),
        )
        .order_by(CrawlRun.created_at.desc())
        .limit(1)
    )
    active = (await db.execute(active_stmt)).scalar_one_or_none()
    if active is not None:
        return active

    latest_stmt = (
        select(CrawlRun)
        .where(
            CrawlRun.source_id == source_id,
            CrawlRun.status != "cancelled",
        )
        .order_by(CrawlRun.created_at.desc())
        .limit(1)
    )
    return (await db.execute(latest_stmt)).scalar_one_or_none()


async def update_crawl_run(
    db: AsyncSession,
    crawl_run_id: str,
    **kwargs: Any,
) -> CrawlRun:
    crawl_run = await get_crawl_run(db, crawl_run_id)
    if crawl_run is None:
        raise ValueError(f"Crawl run {crawl_run_id} not found")
    for key, value in kwargs.items():
        setattr(crawl_run, key, value)
    crawl_run.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(crawl_run)
    return crawl_run


async def upsert_crawl_frontier_rows(
    db: AsyncSession,
    *,
    crawl_run_id: str,
    source_id: str,
    rows: list[dict[str, Any]],
) -> int:
    inserted = 0
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    for row in rows:
        normalized_url = row["normalized_url"]
        payload = dict(
            crawl_run_id=crawl_run_id,
            source_id=source_id,
            mapping_version_id=row.get("mapping_version_id"),
            url=row["url"],
            normalized_url=normalized_url,
            canonical_url=row.get("canonical_url"),
            family_key=row.get("family_key"),
            depth=int(row.get("depth", 0)),
            discovered_from_url=row.get("discovered_from_url"),
            priority=int(row.get("priority", 0)),
            predicted_page_type=row.get("predicted_page_type"),
            discovered_from_page_type=row.get("discovered_from_page_type"),
            discovery_reason=row.get("discovery_reason"),
            status=row.get("status", "discovered"),
            skip_reason=row.get("skip_reason"),
            retry_after=row.get("retry_after"),
            next_retry_at=row.get("next_retry_at"),
            next_eligible_fetch_at=row.get("next_eligible_fetch_at"),
            last_fetched_at=row.get("last_fetched_at"),
            last_extracted_at=row.get("last_extracted_at"),
            content_hash=row.get("content_hash"),
            etag=row.get("etag"),
            last_modified=row.get("last_modified"),
            last_change_detected_at=row.get("last_change_detected_at"),
            last_refresh_outcome=row.get("last_refresh_outcome"),
            diagnostics_json=json.dumps(row.get("diagnostics", {})),
        )
        if dialect_name == "postgresql":
            stmt = pg_insert(CrawlFrontier).values(**payload).on_conflict_do_nothing(
                index_elements=["source_id", "normalized_url"]
            )
            result = await db.execute(stmt)
            inserted += int(result.rowcount or 0)
        elif dialect_name == "sqlite":
            stmt = sqlite_insert(CrawlFrontier).values(**payload).on_conflict_do_nothing(
                index_elements=["source_id", "normalized_url"]
            )
            result = await db.execute(stmt)
            inserted += int(result.rowcount or 0)
        else:
            existing = (
                await db.execute(
                    select(CrawlFrontier).where(
                        CrawlFrontier.source_id == source_id,
                        CrawlFrontier.normalized_url == normalized_url,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(CrawlFrontier(**payload))
                inserted += 1
            else:
                existing.priority = max(existing.priority, int(row.get("priority", existing.priority or 0)))
                if row.get("next_eligible_fetch_at") is not None:
                    existing.next_eligible_fetch_at = row.get("next_eligible_fetch_at")
                if row.get("family_key"):
                    existing.family_key = row.get("family_key")
                existing.updated_at = datetime.now(UTC)
                continue
        existing = (
            await db.execute(
                select(CrawlFrontier).where(
                    CrawlFrontier.source_id == source_id,
                    CrawlFrontier.normalized_url == normalized_url,
                )
            )
        ).scalar_one()
        existing.priority = max(existing.priority, int(row.get("priority", existing.priority or 0)))
        if row.get("next_eligible_fetch_at") is not None:
            existing.next_eligible_fetch_at = row.get("next_eligible_fetch_at")
        if row.get("family_key"):
            existing.family_key = row.get("family_key")
        existing.updated_at = datetime.now(UTC)
    await db.commit()
    return inserted


async def claim_frontier_rows(
    db: AsyncSession,
    *,
    crawl_run_id: str,
    worker_id: str,
    limit: int = 10,
    lease_seconds: int = 120,
) -> list[CrawlFrontier]:
    now = datetime.now(UTC)
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    stmt = (
        select(CrawlFrontier)
        .where(
            CrawlFrontier.crawl_run_id == crawl_run_id,
            CrawlFrontier.status.in_(["queued", "failed_retryable"]),
            or_(
                and_(CrawlFrontier.retry_after.is_(None), CrawlFrontier.next_retry_at.is_(None)),
                CrawlFrontier.retry_after <= now,
                CrawlFrontier.next_retry_at <= now,
            ),
            or_(CrawlFrontier.next_eligible_fetch_at.is_(None), CrawlFrontier.next_eligible_fetch_at <= now),
        )
        .order_by(CrawlFrontier.priority.desc(), CrawlFrontier.depth.asc(), CrawlFrontier.created_at.asc())
        .limit(limit)
    )
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    if dialect_name in {"postgresql", "mysql", "mariadb"}:
        stmt = stmt.with_for_update(skip_locked=True)
        rows = list((await db.execute(stmt)).scalars().all())
        for row in rows:
            row.status = "fetching"
            row.leased_by_worker = worker_id
            row.worker_id = worker_id
            row.started_at = now
            row.lease_expires_at = lease_expires_at
            row.retry_after = None
            row.lease_version = int(row.lease_version or 0) + 1
            row.updated_at = now
        if rows:
            await db.commit()
        return rows

    # App-level atomic claim path for engines without SKIP LOCKED.
    candidate_ids = list((await db.execute(stmt.with_only_columns(CrawlFrontier.id))).scalars().all())
    if not candidate_ids:
        return []
    updated = await db.execute(
        update(CrawlFrontier)
        .where(
            CrawlFrontier.id.in_(candidate_ids),
            CrawlFrontier.status.in_(["queued", "failed_retryable"]),
            or_(
                and_(CrawlFrontier.retry_after.is_(None), CrawlFrontier.next_retry_at.is_(None)),
                CrawlFrontier.retry_after <= now,
                CrawlFrontier.next_retry_at <= now,
            ),
            or_(CrawlFrontier.next_eligible_fetch_at.is_(None), CrawlFrontier.next_eligible_fetch_at <= now),
        )
        .values(
            status="fetching",
            leased_by_worker=worker_id,
            worker_id=worker_id,
            started_at=now,
            lease_expires_at=lease_expires_at,
            retry_after=None,
            lease_version=CrawlFrontier.lease_version + 1,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
        .returning(CrawlFrontier.id)
    )
    claimed_ids = list(updated.scalars().all())
    if not claimed_ids:
        return []
    await db.commit()
    rows = list(
        (
            await db.execute(
                select(CrawlFrontier)
                .where(CrawlFrontier.id.in_(claimed_ids))
                .order_by(CrawlFrontier.priority.desc(), CrawlFrontier.depth.asc(), CrawlFrontier.created_at.asc())
            )
        ).scalars().all()
    )
    return rows


async def update_frontier_row(db: AsyncSession, frontier_id: str, **kwargs: Any) -> CrawlFrontier:
    row = (await db.execute(select(CrawlFrontier).where(CrawlFrontier.id == frontier_id))).scalar_one_or_none()
    if row is None:
        raise ValueError(f"Crawl frontier row {frontier_id} not found")
    new_status = kwargs.get("status")
    if new_status is not None and row.status != new_status:
        allowed_next = FRONTIER_STATUS_TRANSITIONS.get(row.status, set())
        if new_status not in allowed_next:
            logger.warning(
                "invalid_frontier_transition",
                frontier_id=frontier_id,
                from_status=row.status,
                to_status=new_status,
            )
            raise ValueError(f"Invalid frontier status transition: {row.status} -> {new_status}")
    for key, value in kwargs.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return row


async def complete_frontier_row_atomic(
    db: AsyncSession,
    *,
    frontier_id: str,
    worker_id: str,
    lease_version: int,
    page_id: str | None,
    page_updates: dict[str, Any] | None,
    frontier_updates: dict[str, Any],
) -> bool:
    now = datetime.now(UTC)
    frontier = (
        await db.execute(
            select(CrawlFrontier).where(
                CrawlFrontier.id == frontier_id,
                CrawlFrontier.status == "fetching",
                CrawlFrontier.leased_by_worker == worker_id,
                CrawlFrontier.lease_version == lease_version,
            )
        )
    ).scalar_one_or_none()
    if frontier is None:
        return False
    if page_id and page_updates:
        result = await db.execute(
            update(Page)
            .where(Page.id == page_id, Page.status != "completed")
            .values(**page_updates)
        )
        if result.rowcount == 0:
            return False
    for key, value in frontier_updates.items():
        setattr(frontier, key, value)
    frontier.updated_at = now
    await db.commit()
    return True


async def reclaim_expired_frontier_leases(
    db: AsyncSession,
    *,
    crawl_run_id: str,
) -> int:
    now = datetime.now(UTC)
    rows = list(
        (
            await db.execute(
                select(CrawlFrontier).where(
                    CrawlFrontier.crawl_run_id == crawl_run_id,
                    CrawlFrontier.status == "fetching",
                    CrawlFrontier.lease_expires_at.is_not(None),
                    CrawlFrontier.lease_expires_at < now,
                )
            )
        ).scalars().all()
    )
    reclaimed = 0
    for row in rows:
        result = await db.execute(
            update(CrawlFrontier)
            .execution_options(synchronize_session=False)
            .where(
                CrawlFrontier.id == row.id,
                CrawlFrontier.status == "fetching",
                CrawlFrontier.lease_version == row.lease_version,
                CrawlFrontier.lease_expires_at.is_not(None),
                CrawlFrontier.lease_expires_at < now,
            )
            .values(
                status="queued",
                leased_by_worker=None,
                worker_id=None,
                started_at=None,
                lease_expires_at=None,
                lease_version=CrawlFrontier.lease_version + 1,
                last_error="lease_expired_reset_to_queue",
                updated_at=now,
            )
        )
        reclaimed += int(result.rowcount or 0)
    if reclaimed:
        await db.commit()
    return reclaimed


async def recover_stale_in_progress_pages(
    db: AsyncSession,
    *,
    source_id: str,
    stale_after_seconds: int,
) -> int:
    threshold = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
    rows = list(
        (
            await db.execute(
                select(Page).where(
                    Page.source_id == source_id,
                    Page.status == "in_progress",
                    Page.started_at.is_not(None),
                    Page.started_at < threshold,
                )
            )
        ).scalars().all()
    )
    for row in rows:
        row.status = "pending"
        row.worker_id = None
        row.started_at = None
        row.error_message = "recovered_from_stale_in_progress"
    if rows:
        await db.commit()
    return len(rows)


async def acquire_domain_rate_limit_slot(
    db: AsyncSession,
    *,
    domain: str,
    min_interval_ms: int,
) -> tuple[bool, datetime]:
    now = datetime.now(UTC)
    next_allowed = now + timedelta(milliseconds=min_interval_ms)
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    if dialect_name == "postgresql":
        stmt = (
            pg_insert(DomainRateLimit)
            .values(domain=domain, next_allowed_at=next_allowed)
            .on_conflict_do_update(
                index_elements=["domain"],
                set_={"next_allowed_at": next_allowed, "updated_at": now},
                where=DomainRateLimit.next_allowed_at <= now,
            )
            .returning(DomainRateLimit.next_allowed_at)
        )
    else:
        stmt = (
            sqlite_insert(DomainRateLimit)
            .values(domain=domain, next_allowed_at=next_allowed)
            .on_conflict_do_update(
                index_elements=["domain"],
                set_={"next_allowed_at": next_allowed, "updated_at": now},
                where=DomainRateLimit.next_allowed_at <= now,
            )
            .returning(DomainRateLimit.next_allowed_at)
        )
    result = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    if result is not None:
        return True, _ensure_utc(now) or now
    current = await db.get(DomainRateLimit, domain)
    return False, (_ensure_utc(current.next_allowed_at) if current else _ensure_utc(now) or now)


async def get_crawl_frontier_counts(db: AsyncSession, crawl_run_id: str) -> dict[str, int]:
    stmt = (
        select(CrawlFrontier.status, func.count(CrawlFrontier.id))
        .where(CrawlFrontier.crawl_run_id == crawl_run_id)
        .group_by(CrawlFrontier.status)
    )
    rows = (await db.execute(stmt)).all()
    return {status: int(count) for status, count in rows}


async def count_crawl_frontier_rows_by_error(
    db: AsyncSession,
    *,
    crawl_run_id: str,
    last_error: str,
) -> int:
    stmt = select(func.count(CrawlFrontier.id)).where(
        CrawlFrontier.crawl_run_id == crawl_run_id,
        CrawlFrontier.last_error == last_error,
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def upsert_crawl_run_checkpoint(
    db: AsyncSession,
    *,
    crawl_run_id: str,
    source_id: str,
    mapping_version_id: str | None,
    status: str,
    frontier_counts: dict[str, int],
    last_processed_url: str | None = None,
    progress: dict[str, Any] | None = None,
    worker_state: dict[str, Any] | None = None,
) -> CrawlRunCheckpoint:
    existing = (
        await db.execute(select(CrawlRunCheckpoint).where(CrawlRunCheckpoint.crawl_run_id == crawl_run_id))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing is None:
        existing = CrawlRunCheckpoint(
            crawl_run_id=crawl_run_id,
            source_id=source_id,
            mapping_version_id=mapping_version_id,
            status=status,
            frontier_counts_json=json.dumps(frontier_counts),
            last_processed_url=last_processed_url,
            progress_json=json.dumps(progress or {}),
            worker_state_json=json.dumps(worker_state or {}),
            last_checkpoint_at=now,
        )
        db.add(existing)
    else:
        existing.status = status
        existing.mapping_version_id = mapping_version_id
        existing.frontier_counts_json = json.dumps(frontier_counts)
        existing.last_processed_url = last_processed_url
        existing.progress_json = json.dumps(progress or {})
        existing.worker_state_json = json.dumps(worker_state or {})
        existing.last_checkpoint_at = now
        existing.updated_at = now
    await db.commit()
    await db.refresh(existing)
    return existing


async def get_crawl_run_checkpoint(db: AsyncSession, crawl_run_id: str) -> CrawlRunCheckpoint | None:
    return (
        await db.execute(select(CrawlRunCheckpoint).where(CrawlRunCheckpoint.crawl_run_id == crawl_run_id))
    ).scalar_one_or_none()


async def queue_discovered_frontier_rows(db: AsyncSession, *, crawl_run_id: str, limit: int = 100) -> int:
    rows = list(
        (
            await db.execute(
                select(CrawlFrontier)
                .where(
                    CrawlFrontier.crawl_run_id == crawl_run_id,
                    CrawlFrontier.status == "discovered",
                )
                .order_by(CrawlFrontier.created_at.asc())
                .limit(limit)
            )
        ).scalars().all()
    )
    now = datetime.now(UTC)
    for row in rows:
        row.status = "queued"
        row.updated_at = now
    if rows:
        await db.commit()
    return len(rows)


async def requeue_retryable_frontier_rows(db: AsyncSession, *, crawl_run_id: str, limit: int = 1000) -> int:
    rows = list(
        (
            await db.execute(
                select(CrawlFrontier)
                .where(
                    CrawlFrontier.crawl_run_id == crawl_run_id,
                    CrawlFrontier.status == "failed_retryable",
                )
                .order_by(CrawlFrontier.updated_at.asc())
                .limit(limit)
            )
        ).scalars().all()
    )
    now = datetime.now(UTC)
    for row in rows:
        row.status = "queued"
        row.next_retry_at = now
        row.updated_at = now
    if rows:
        await db.commit()
    return len(rows)


async def get_refresh_eligibility_counts(
    db: AsyncSession,
    *,
    source_id: str,
    mapping_version_id: str,
    as_of: datetime | None = None,
) -> dict[str, int]:
    now = as_of or datetime.now(UTC)
    base_stmt = select(CrawlFrontier).where(
        CrawlFrontier.source_id == source_id,
        CrawlFrontier.mapping_version_id == mapping_version_id,
    )
    rows = list((await db.execute(base_stmt)).scalars().all())
    eligible = 0
    skipped_not_due = 0
    for row in rows:
        next_eligible = _ensure_utc(row.next_eligible_fetch_at)
        if next_eligible is None or next_eligible <= now:
            eligible += 1
        else:
            skipped_not_due += 1
    return {
        "total": len(rows),
        "eligible": eligible,
        "skipped_not_due": skipped_not_due,
    }


async def prepare_refresh_frontier_rows(
    db: AsyncSession,
    *,
    crawl_run_id: str,
    source_id: str,
    mapping_version_id: str,
    force: bool = False,
    limit: int = 1000,
    as_of: datetime | None = None,
) -> dict[str, int]:
    now = as_of or datetime.now(UTC)
    stmt = (
        select(CrawlFrontier)
        .where(
            CrawlFrontier.source_id == source_id,
            CrawlFrontier.mapping_version_id == mapping_version_id,
        )
        .order_by(CrawlFrontier.updated_at.asc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    selected = 0
    skipped_not_due = 0
    for row in rows:
        next_eligible = _ensure_utc(row.next_eligible_fetch_at)
        due = next_eligible is None or next_eligible <= now
        if not force and not due:
            skipped_not_due += 1
            continue
        row.crawl_run_id = crawl_run_id
        row.status = "queued"
        row.skip_reason = None
        row.leased_by_worker = None
        row.lease_expires_at = None
        row.last_error = None
        row.next_retry_at = None
        row.updated_at = now
        selected += 1
    if rows:
        await db.commit()
    return {
        "selected": selected,
        "skipped_not_due": skipped_not_due,
    }
    normalized_drift_type = drift_type or signal_type.upper()
    if normalized_drift_type not in DRIFT_SIGNAL_TYPES:
        normalized_drift_type = "VALUE_ANOMALY"
