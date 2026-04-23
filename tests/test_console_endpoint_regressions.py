from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


async def test_console_endpoints_return_non_error_on_empty_db(test_client: AsyncClient):
    records = await test_client.get("/api/records", params={"limit": 5})
    assert records.status_code == 200
    assert records.json()["items"] == []

    review = await test_client.get("/api/review/artists", params={"has_conflicts": "true"})
    assert review.status_code == 200
    assert review.json()["items"] == []

    semantic = await test_client.get("/api/semantic/artists", params={"q": "abstract expressionism"})
    assert semantic.status_code == 200
    assert semantic.json()["items"] == []


async def test_console_404_endpoints_are_now_present(test_client: AsyncClient):
    mappings = await test_client.get("/api/mappings")
    assert mappings.status_code == 200
    assert "items" in mappings.json()

    merge_candidates = await test_client.get("/api/entities/merge-candidates")
    assert merge_candidates.status_code == 200
    assert "items" in merge_candidates.json()


async def test_records_endpoint_tolerates_malformed_confidence_score(
    test_client: AsyncClient, db_session: AsyncSession
):
    source = await crud.create_source(db_session, url="https://records-regression.test")
    record = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Broken Score Artist",
    )
    await db_session.execute(
        text("UPDATE records SET confidence_score = 'not-a-number' WHERE id = :record_id"),
        {"record_id": record.id},
    )
    await db_session.commit()
    raw_score = (
        await db_session.execute(text("SELECT confidence_score FROM records WHERE id = :record_id"), {"record_id": record.id})
    ).scalar_one()
    assert str(raw_score) == "not-a-number"

    response = await test_client.get("/api/records", params={"limit": 5})
    assert response.status_code == 200
    assert response.json()["items"][0]["confidence_score"] == 0


async def test_duplicates_and_semantic_endpoints_tolerate_bad_embeddings(
    test_client: AsyncClient, db_session: AsyncSession
):
    source = await crud.create_source(db_session, url="https://embedding-regression.test")
    first = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Artist One",
    )
    second = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Artist Two",
    )
    await db_session.execute(
        text("UPDATE records SET embedding_vector = '[\"bad\", 1]' WHERE id = :record_id"),
        {"record_id": first.id},
    )
    await db_session.execute(
        text("UPDATE records SET embedding_vector = '[\"bad\", 1]' WHERE id = :record_id"),
        {"record_id": second.id},
    )
    await db_session.commit()
    raw_embedding = (
        await db_session.execute(text("SELECT embedding_vector FROM records WHERE id = :record_id"), {"record_id": first.id})
    ).scalar_one()
    assert raw_embedding == "[\"bad\", 1]"

    duplicates = await test_client.get("/api/suggest/duplicates", params={"auto_merge": "false"})
    assert duplicates.status_code == 200
    assert "items" in duplicates.json()

    semantic = await test_client.get("/api/semantic/artists", params={"q": "abstract expressionism"})
    assert semantic.status_code == 200
    assert "items" in semantic.json()


def test_parse_embedding_handles_non_string_runtime_shapes():
    assert crud.parse_embedding([0.1, "0.2", 3]) == [0.1, 0.2, 3.0]
    assert crud.parse_embedding('["bad", 1]') == []
    assert crud.parse_embedding(["bad", 1]) == []
    assert crud.parse_embedding({"embedding": [1, 2]}) == []
