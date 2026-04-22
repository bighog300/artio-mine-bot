import json

import pytest

from app.db import crud
from app.records.deduplication import classify_identity_match
from app.records.schema import RecordType


@pytest.mark.asyncio
async def test_duplicate_insert_prevention(db_session):
    source = await crud.create_source(db_session, url="https://example.com", name="Example")

    left = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="ARTIST",
        title="Jane Doe",
        website_url="https://janedoe.example",
        confidence_score=70,
    )
    right = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Jane Doe",
        website_url="https://janedoe.example",
        confidence_score=60,
    )

    assert left.id == right.id
    records = await crud.list_records(db_session, source_id=source.id, record_type="artist", limit=20)
    assert len(records) == 1


@pytest.mark.asyncio
async def test_merge_correctness_prefers_higher_confidence_and_unions_arrays(db_session):
    source = await crud.create_source(db_session, url="https://example.org", name="Example Org")

    record = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Mary Smith",
        description="Short bio",
        website_url="https://marysmith.example",
        mediums=["oil"],
        confidence_score=60,
        field_confidence={"description": 60, "mediums": 60},
    )

    merged = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Mary Smith",
        description="Longer verified biography",
        website_url="https://marysmith.example",
        mediums=["oil", "ink"],
        confidence_score=90,
        field_confidence={"description": 90, "mediums": 80},
    )

    assert merged.id == record.id
    assert merged.description == "Longer verified biography"
    assert set(json.loads(merged.mediums)) == {"oil", "ink"}


@pytest.mark.asyncio
async def test_multi_page_same_artist_merges_into_one_entity(db_session):
    source = await crud.create_source(db_session, url="https://example.net", name="Example Net")
    page_a = await crud.create_page(db_session, source_id=source.id, url="https://example.net/a")
    page_b = await crud.create_page(db_session, source_id=source.id, url="https://example.net/b")

    first = await crud.create_record(
        db_session,
        source_id=source.id,
        page_id=page_a.id,
        record_type="artist",
        title="Artist Alpha",
        bio="Bio A",
        website_url="https://artist.example.net",
        confidence_score=75,
    )
    second = await crud.create_record(
        db_session,
        source_id=source.id,
        page_id=page_b.id,
        record_type="artist",
        title="Artist Alpha",
        website_url="https://artist.example.net",
        confidence_score=80,
    )

    assert first.id == second.id
    assert second.website_url == "https://artist.example.net"


@pytest.mark.asyncio
async def test_conflicting_data_resolution_uses_field_confidence(db_session):
    source = await crud.create_source(db_session, url="https://venue.example", name="Venue")

    original = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Gallery One",
        address="10 Art St",
        city="Cape Town",
        confidence_score=85,
        field_confidence={"address": 85, "city": 85},
    )
    merged = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Gallery One",
        address="10 Art St",
        city="Johannesburg",
        confidence_score=40,
        field_confidence={"address": 40, "city": 40},
    )

    assert merged.id == original.id
    assert merged.city == "Cape Town"
    assert merged.structured_data["city"] == "Cape Town"


@pytest.mark.asyncio
async def test_false_merge_prevention_without_secondary_signal(db_session):
    source = await crud.create_source(db_session, url="https://false-merge.example", name="False Merge")
    one = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alex Brown",
        bio="Painter from Cape Town",
        confidence_score=70,
    )
    two = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alex Brown",
        bio="Sculptor from Nairobi",
        confidence_score=68,
    )
    assert one.id != two.id


@pytest.mark.asyncio
async def test_similar_name_different_entity_does_not_merge(db_session):
    source = await crud.create_source(db_session, url="https://name-similarity.example", name="Name Similarity")
    first = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Modern Art House",
        address="1 Main Road",
        city="Cape Town",
        confidence_score=85,
        field_confidence={"address": 85, "city": 85},
    )
    second = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Modern Arts Hub",
        address="88 South Ave",
        city="Durban",
        confidence_score=82,
        field_confidence={"address": 82, "city": 82},
    )
    assert first.id != second.id


@pytest.mark.asyncio
async def test_conflict_detection_preserves_existing_value(db_session):
    source = await crud.create_source(db_session, url="https://conflict-detection.example", name="Conflict Detection")
    primary = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Lina Moss",
        website_url="https://linamoss.example",
        birth_year=1980,
        confidence_score=90,
        field_confidence={"birth_year": 90},
    )
    merged = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Lina Moss",
        website_url="https://linamoss.example",
        birth_year=1982,
        confidence_score=92,
        field_confidence={"birth_year": 92},
    )
    assert merged.id == primary.id
    assert merged.birth_year == 1980
    assert merged.has_conflicts is True
    payload = json.loads(merged.raw_data or "{}")
    assert "birth_year" in payload.get("conflicts", {})


@pytest.mark.asyncio
async def test_review_band_persists_duplicate_candidate(db_session):
    source = await crud.create_source(db_session, url="https://review-band.example", name="Review Band")
    first = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alex Brown",
        confidence_score=75,
    )
    second = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alex Browne",
        confidence_score=72,
    )
    assert first.id != second.id

    reviews = await crud.list_duplicate_reviews(db_session, status="pending", limit=20)
    review = next((item for item in reviews if {item.left_record_id, item.right_record_id} == {first.id, second.id}), None)
    assert review is not None
    assert review.needs_review is True
    assert 70 <= review.similarity_score <= 85


def test_strong_signal_required_for_merge_decision():
    score, decision, signals = classify_identity_match(
        record_type=RecordType.ARTIST,
        existing_values={
            "normalized_name": "alex brown",
            "nationality": "South African",
        },
        incoming_values={
            "normalized_name": "alex brown",
            "nationality": "South African",
        },
    )
    assert score >= 0.85
    assert decision == "review"
    assert signals["strong_secondary_signal"] is False
