import json

import pytest

from app.db import crud
from app.db.models import Entity, EntityLink, EntityRelationship
from app.entities.relationship_builder import EntityRelationshipBuilder
from app.entities.resolver import EntityResolver


@pytest.mark.asyncio
async def test_same_artist_across_sources_single_entity(db_session):
    source_a = await crud.create_source(db_session, "https://source-a.example", "A")
    source_b = await crud.create_source(db_session, "https://source-b.example", "B")

    record_a = await crud.create_record(
        db_session,
        source_id=source_a.id,
        record_type="artist",
        title="Jane Doe",
        nationality="South African",
        birth_year=1987,
        confidence_score=95,
    )
    record_b = await crud.create_record(
        db_session,
        source_id=source_b.id,
        record_type="artist",
        title="Jane Doe",
        nationality="South African",
        birth_year=1987,
        confidence_score=90,
    )

    resolver = EntityResolver(db_session)
    result_a = await resolver.resolve_record(record_a)
    result_b = await resolver.resolve_record(record_b)

    assert result_a.entity.id == result_b.entity.id
    links = (await db_session.execute(EntityLink.__table__.select())).all()
    assert len(links) == 2


@pytest.mark.asyncio
async def test_similar_name_different_artists_not_merged(db_session):
    source_a = await crud.create_source(db_session, "https://s1.example", "S1")
    source_b = await crud.create_source(db_session, "https://s2.example", "S2")

    record_a = await crud.create_record(
        db_session,
        source_id=source_a.id,
        record_type="artist",
        title="Alex Kim",
        nationality="Korean",
        birth_year=1980,
        confidence_score=92,
    )
    record_b = await crud.create_record(
        db_session,
        source_id=source_b.id,
        record_type="artist",
        title="Alec Kim",
        nationality="Canadian",
        birth_year=1996,
        confidence_score=92,
    )

    resolver = EntityResolver(db_session)
    result_a = await resolver.resolve_record(record_a)
    result_b = await resolver.resolve_record(record_b)

    assert result_a.entity.id != result_b.entity.id


@pytest.mark.asyncio
async def test_canonical_merge_prefers_high_confidence(db_session):
    source = await crud.create_source(db_session, "https://merge.example", "Merge")
    source_two = await crud.create_source(db_session, "https://merge-2.example", "Merge 2")
    high = await crud.create_record(
        db_session,
        source_id=source_two.id,
        record_type="venue",
        title="Central Gallery",
        description="Trusted description",
        address="10 Main Street",
        city="Cape Town",
        confidence_score=95,
    )
    low = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Central Gallery",
        description="Lower confidence description",
        address="10 Main Street",
        city="Cape Town",
        confidence_score=45,
    )

    resolver = EntityResolver(db_session)
    high_result = await resolver.resolve_record(high)
    low_result = await resolver.resolve_record(low)

    assert high_result.entity.id == low_result.entity.id
    entity = await db_session.get(Entity, high_result.entity.id)
    assert entity is not None
    assert entity.canonical_data["fields"]["description"] == "Trusted description"
    assert len(entity.canonical_data.get("conflicts", [])) >= 1


@pytest.mark.asyncio
async def test_relationship_creation_correctness(db_session):
    source = await crud.create_source(db_session, "https://graph.example", "Graph")
    artist = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Nora Muse",
        confidence_score=90,
    )
    artwork = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artwork",
        title="Blue Horizon",
        artist_names=json.dumps(["Nora Muse"]),
        confidence_score=88,
    )

    resolver = EntityResolver(db_session)
    await resolver.resolve_record(artist)
    await resolver.resolve_record(artwork)

    builder = EntityRelationshipBuilder(db_session)
    created = await builder.build_for_record(artwork)

    assert created == 1
    relationships = (await db_session.execute(EntityRelationship.__table__.select())).all()
    assert len(relationships) == 1
    assert relationships[0].relationship_type == "CREATED_BY"


@pytest.mark.asyncio
async def test_no_cross_type_linking_errors(db_session):
    source = await crud.create_source(db_session, "https://cross-type.example", "Cross")
    artist = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Modern Hall",
        confidence_score=91,
    )
    venue = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="venue",
        title="Modern Hall",
        address="1 Museum Rd",
        confidence_score=91,
    )

    resolver = EntityResolver(db_session)
    artist_result = await resolver.resolve_record(artist)
    venue_result = await resolver.resolve_record(venue)

    assert artist_result.entity.entity_type == "artist"
    assert venue_result.entity.entity_type == "venue"
    assert artist_result.entity.id != venue_result.entity.id


@pytest.mark.asyncio
async def test_entities_api_endpoints(test_client, db_session):
    source = await crud.create_source(db_session, "https://api-entity.example", "API")
    record = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="API Artist",
        confidence_score=90,
    )
    resolver = EntityResolver(db_session)
    resolution = await resolver.resolve_record(record)

    entities_response = await test_client.get("/api/entities")
    assert entities_response.status_code == 200
    assert entities_response.json()["total"] >= 1

    detail_response = await test_client.get(f"/api/entities/{resolution.entity.id}")
    assert detail_response.status_code == 200

    records_response = await test_client.get(f"/api/entities/{resolution.entity.id}/records")
    assert records_response.status_code == 200
    assert any(item["id"] == record.id for item in records_response.json())

    relationships_response = await test_client.get(f"/api/entities/{resolution.entity.id}/relationships")
    assert relationships_response.status_code == 200
