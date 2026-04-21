from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

MIN_REALTIME_INTERVAL = timedelta(minutes=5)


def normalize_freshness_policy(policy: str | None) -> str:
    value = (policy or "").strip().lower()
    if value in {"realtime", "daily", "weekly", "monthly", "manual"}:
        return value
    return "daily"


def compute_next_eligible_fetch_at(
    *,
    policy: str | None,
    now: datetime,
) -> datetime | None:
    normalized = normalize_freshness_policy(policy)
    if normalized == "manual":
        return None
    if normalized == "realtime":
        return now + MIN_REALTIME_INTERVAL
    if normalized == "weekly":
        return now + timedelta(days=7)
    if normalized == "monthly":
        return now + timedelta(days=30)
    return now + timedelta(days=1)


@dataclass
class ChangeDetectionResult:
    changed: bool
    reason: str


def detect_content_change(
    *,
    previous_content_hash: str | None,
    new_content_hash: str | None,
    previous_etag: str | None,
    new_etag: str | None,
    previous_last_modified: str | None,
    new_last_modified: str | None,
) -> ChangeDetectionResult:
    if previous_content_hash and new_content_hash and previous_content_hash != new_content_hash:
        return ChangeDetectionResult(changed=True, reason="content_hash")
    if previous_etag and new_etag and previous_etag != new_etag:
        return ChangeDetectionResult(changed=True, reason="etag")
    if (
        previous_last_modified
        and new_last_modified
        and previous_last_modified != new_last_modified
    ):
        return ChangeDetectionResult(changed=True, reason="last_modified")
    return ChangeDetectionResult(changed=False, reason="unchanged")


def utcnow() -> datetime:
    return datetime.now(UTC)
