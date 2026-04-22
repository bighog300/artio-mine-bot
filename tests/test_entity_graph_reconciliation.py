import json

import pytest
from sqlalchemy import select

from app.db import crud
from app.db.models import Entity, EntityLink, EntityRelationship
from app.entities.reconciliation import EntityGraphReconciler
from app.entities.relationship_builder import EntityRelationshipBuilder
from app.entities.resolver import EntityResolver


@pytest.mark.asyncio
async def test_entity_merge_operation_reassigns_links_and_soft_deletes(db_session):
    source = await crud.create_source(db_session, "https://merge-op.example", "MergeOp")
    source_id = source.id

    record_a = await crud.create_record(db_session, source_id=source_id, record_type="artist", title="Lina Hart", confidence_score=95)
    record_c = await crud.create_record(db_session, source_id=source_id, record_type="artist", title="Lina Hart", confidence_score=65)

    resolver = EntityResolver(db_session)
    res_a = await resolver.resolve_record(record_a)

    # force a separate duplicate entity to test explicit merge path
    duplicate = Entity(
        source_id=source_id,
        entity_type="artist",
        canonical_name="Lina Hart",
        canonical_data={"fields": {"title": "Lina Hart", "nationality": "ZA"}, "provenance": {}, "conflicts": []},
        confidence_score=0.6,
    )
    db_session.add(duplicate)
    await db_session.commit()
    await db_session.refresh(duplicate)

    link = EntityLink(entity_id=duplicate.id, record_id=record_c.id, source_id=source_id, confidence_score=0.7, match_method="fuzzy")
    db_session.add(link)
    await db_session.commit()

    reconciler = EntityGraphReconciler(db_session)
    winner = await reconciler.merge_entities(res_a.entity.id, duplicate.id)

    refreshed_a = await db_session.get(Entity, res_a.entity.id)
    refreshed_dup = await db_session.get(Entity, duplicate.id)
    assert refreshed_a is not None and refreshed_dup is not None
    deleted = [entity for entity in (refreshed_a, refreshed_dup) if entity.is_deleted]
    assert len(deleted) == 1
    assert deleted[0].merged_into_entity_id == winner.id

    link_count = (await db_session.execute(select(EntityLink).where(EntityLink.entity_id == winner.id))).scalars().all()
    assert len(link_count) >= 2


@pytest.mark.asyncio
async def test_reconciliation_loop_uses_blocking_and_merges_strong_matches(db_session):
    source = await crud.create_source(db_session, "https://reconcile.example", "Reconcile")
    source_id = source.id
    resolver = EntityResolver(db_session)

    for name in ["Aria Stone", "Aria Stone", "Aria Stonn", "Bex Carter"]:
        record = await crud.create_record(db_session, source_id=source_id, record_type="artist", title=name, confidence_score=90)
        await resolver.resolve_record(record)

    loose = Entity(source_id=source_id, entity_type="artist", canonical_name="Aria Stone", canonical_data={"fields": {"title": "Aria Stone"}}, confidence_score=0.55)
    db_session.add(loose)
    await db_session.commit()

    reconciler = EntityGraphReconciler(db_session)
    stats = await reconciler.run_reconciliation_pass(min_match_score=0.96, block_prefix_len=3)

    assert stats["scanned_pairs"] > 0
    assert stats["merged_pairs"] >= 1


@pytest.mark.asyncio
async def test_relationship_dedup_and_confidence_aggregation(db_session):
    source = await crud.create_source(db_session, "https://rels.example", "Rels")
    source_id = source.id
    resolver = EntityResolver(db_session)

    artist_record = await crud.create_record(db_session, source_id=source_id, record_type="artist", title="Mika Lane", confidence_score=88)
    artwork_1 = await crud.create_record(
        db_session,
        source_id=source_id,
        record_type="artwork",
        title="Work One",
        artist_names=json.dumps(["Mika Lane"]),
        confidence_score=62,
    )
    await resolver.resolve_record(artist_record)
    await resolver.resolve_record(artwork_1)

    builder = EntityRelationshipBuilder(db_session)
    await builder.build_for_record(artwork_1)
    await builder.build_for_record(artwork_1)

    rows = (await db_session.execute(select(EntityRelationship))).scalars().all()
    assert len(rows) == 1
    metadata = json.loads(rows[0].metadata_json or "{}")
    assert int(metadata.get("reinforcement_count", 0)) >= 2


@pytest.mark.asyncio
async def test_entity_confidence_and_canonical_recompute(db_session):
    source_a = await crud.create_source(db_session, "https://confidence-a.example", "A")
    source_b = await crud.create_source(db_session, "https://confidence-b.example", "B")

    resolver = EntityResolver(db_session)
    record_a = await crud.create_record(
        db_session,
        source_id=source_a.id,
        record_type="venue",
        title="North Hall",
        city="Cape Town",
        description="Primary description",
        confidence_score=92,
    )
    record_b = await crud.create_record(
        db_session,
        source_id=source_b.id,
        record_type="venue",
        title="North Hall",
        city="Cape Town",
        description="Secondary description",
        confidence_score=70,
    )

    res_a = await resolver.resolve_record(record_a)
    await resolver.resolve_record(record_b)

    reconciler = EntityGraphReconciler(db_session)
    entity = await reconciler.recompute_canonical_data(res_a.entity.id)

    assert entity.canonical_data["fields"]["description"] in {"Primary description", "Secondary description"}
    assert entity.confidence_score > 0.0
