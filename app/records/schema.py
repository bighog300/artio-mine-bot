from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecordType(str, Enum):
    ARTIST = "artist"
    ARTWORK = "artwork"
    EXHIBITION = "exhibition"
    EVENT = "event"
    VENUE = "venue"
    ORGANIZATION = "organization"


class RecordData(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str | None = None
    description: str | None = None
    bio: str | None = None
    source_url: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    artist_names: list[str] = Field(default_factory=list)
    ticket_url: str | None = None
    is_free: bool | None = None
    price_text: str | None = None
    curator: str | None = None
    nationality: str | None = None
    birth_year: int | None = None
    mediums: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
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


class StructuredRecordPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    record_type: RecordType
    normalized_name: str
    fingerprint: str
    fingerprint_version: str = "v2"
    data: RecordData
    field_confidence: dict[str, float] = Field(default_factory=dict)
    confidence_score: int = 0

    @classmethod
    def from_values(
        cls,
        *,
        record_type: RecordType,
        normalized_name: str,
        fingerprint: str,
        fingerprint_version: str,
        values: dict[str, Any],
        field_confidence: dict[str, float],
        confidence_score: int,
    ) -> "StructuredRecordPayload":
        return cls(
            record_type=record_type,
            normalized_name=normalized_name,
            fingerprint=fingerprint,
            fingerprint_version=fingerprint_version,
            data=RecordData.model_validate(values),
            field_confidence=field_confidence,
            confidence_score=confidence_score,
        )
