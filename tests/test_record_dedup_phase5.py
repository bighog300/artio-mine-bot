import json

import pytest

from app.db import crud


@pytest.mark.asyncio
async def test_duplicate_insert_prevention(db_session):
    source = await crud.create_source(db_session, url="https://example.com", name="Example")

    left = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="ARTIST",
        title="Jane Doe",
        confidence_score=70,
    )
    right = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Jane Doe",
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
        city="Cape Town",
        confidence_score=85,
        field_confidence={"city": 85},
    )
    merged = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Gallery One",
        city="Johannesburg",
        confidence_score=40,
        field_confidence={"city": 40},
    )

    assert merged.id == original.id
    assert merged.city == "Cape Town"
    assert merged.structured_data["city"] == "Cape Town"
