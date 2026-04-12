import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


@pytest.mark.asyncio
async def test_create_source(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com", name="Example")
    assert source.id is not None
    assert source.url == "https://example.com"
    assert source.name == "Example"
    assert source.status == "pending"


@pytest.mark.asyncio
async def test_get_source(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    fetched = await crud.get_source(db_session, source.id)
    assert fetched is not None
    assert fetched.id == source.id


@pytest.mark.asyncio
async def test_create_page(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://example.com/artists/",
        original_url="https://example.com/artists/",
        depth=1,
    )
    assert page.id is not None
    assert page.source_id == source.id
    assert page.url == "https://example.com/artists/"
    assert page.depth == 1


@pytest.mark.asyncio
async def test_create_record_json_defaults(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    record = await crud.create_record(db_session, source_id=source.id, record_type="artist")
    assert record.id is not None
    assert record.artist_names == "[]"
    assert record.mediums == "[]"
    assert record.collections == "[]"


@pytest.mark.asyncio
async def test_create_image(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    page = await crud.create_page(db_session, source_id=source.id, url="https://example.com/p1")
    record = await crud.create_record(
        db_session, source_id=source.id, record_type="artist", page_id=page.id
    )
    image = await crud.create_image(
        db_session,
        source_id=source.id,
        url="https://example.com/img.jpg",
        record_id=record.id,
        is_valid=True,
    )
    assert image.id is not None
    assert image.record_id == record.id
    assert image.is_valid is True


@pytest.mark.asyncio
async def test_create_job(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    job = await crud.create_job(
        db_session, source_id=source.id, job_type="map_site", payload={"key": "value"}
    )
    assert job.id is not None
    assert job.source_id == source.id
    assert job.job_type == "map_site"
    assert job.status == "pending"


@pytest.mark.asyncio
async def test_update_source(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    updated = await crud.update_source(db_session, source.id, name="Updated", status="mapping")
    assert updated.name == "Updated"
    assert updated.status == "mapping"


@pytest.mark.asyncio
async def test_bulk_approve(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://example.com")
    # Create records with different confidence scores
    r1 = await crud.create_record(
        db_session, source_id=source.id, record_type="artist",
        title="Artist 1", confidence_score=85, confidence_band="HIGH"
    )
    r2 = await crud.create_record(
        db_session, source_id=source.id, record_type="artist",
        title="Artist 2", confidence_score=30, confidence_band="LOW"
    )
    count = await crud.bulk_approve(db_session, source.id, min_confidence=70)
    assert count == 1

    updated_r1 = await crud.get_record(db_session, r1.id)
    updated_r2 = await crud.get_record(db_session, r2.id)
    assert updated_r1.status == "approved"
    assert updated_r2.status == "pending"
