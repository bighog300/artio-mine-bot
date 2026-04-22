import pytest

from app.db import crud
from app.pipeline.drift_detection import DriftDetectionService


@pytest.mark.asyncio
async def test_missing_field_detection_emits_high_signal(db_session):
    source = await crud.create_source(db_session, url="https://drift-fields.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    await crud.update_source(db_session, source.id, published_mapping_version_id=mapping.id, active_mapping_version_id=mapping.id)
    page = await crud.create_page(
        db_session,
        source.id,
        "https://drift-fields.test/event/1",
        page_type="event_detail",
        status="extracted",
        mapping_version_id_used=mapping.id,
        template_hash="tpl-v1",
    )
    await crud.upsert_extraction_baseline(
        db_session,
        source_id=source.id,
        page_id=page.id,
        mapping_version_id=mapping.id,
        record_id=None,
        baseline={"title": "Old title", "start_date": "2026-04-12", "source_url": page.url},
        field_stats={},
        dom_section_hash="tpl-v1",
        confidence_score=90,
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="event",
        page_id=page.id,
        source_url=page.url,
        title=None,
        start_date="2026-04-12",
        confidence_score=90,
        confidence_band="HIGH",
    )

    summary = await DriftDetectionService(db_session).analyze_source(source.id)
    assert summary["pages_with_drift"] == 1
    signals = await crud.list_mapping_drift_signals(db_session, source_id=source.id)
    assert any(s.drift_type == "FIELD_MISSING" and s.severity == "high" for s in signals)


@pytest.mark.asyncio
async def test_selector_fail_and_structure_change_detection(db_session):
    source = await crud.create_source(db_session, url="https://drift-structure.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    await crud.update_source(db_session, source.id, published_mapping_version_id=mapping.id, active_mapping_version_id=mapping.id)
    page = await crud.create_page(
        db_session,
        source.id,
        "https://drift-structure.test/artist/1",
        page_type="artist_profile",
        status="extracted",
        mapping_version_id_used=mapping.id,
        template_hash="tpl-v2",
        error_message="Selector lookup failed for .artist-bio",
    )
    await crud.upsert_extraction_baseline(
        db_session,
        source_id=source.id,
        page_id=page.id,
        mapping_version_id=mapping.id,
        record_id=None,
        baseline={"title": "Artist A", "source_url": page.url},
        field_stats={},
        dom_section_hash="tpl-v1",
        confidence_score=80,
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        page_id=page.id,
        source_url=page.url,
        title="Artist A",
        confidence_score=70,
        confidence_band="MEDIUM",
    )

    await DriftDetectionService(db_session).analyze_source(source.id)
    signals = await crud.list_mapping_drift_signals(db_session, source_id=source.id)
    drift_types = {s.drift_type for s in signals}
    assert "SELECTOR_FAIL" in drift_types
    assert "STRUCTURE_CHANGED" in drift_types


@pytest.mark.asyncio
async def test_drift_aggregation_escalates_and_pauses_source(db_session):
    source = await crud.create_source(db_session, url="https://drift-aggregate.test")
    source_id = source.id
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping_id = mapping.id
    await crud.update_source(db_session, source_id, published_mapping_version_id=mapping_id, active_mapping_version_id=mapping_id)

    for idx in range(5):
        page = await crud.create_page(
            db_session,
            source_id,
            f"https://drift-aggregate.test/event/{idx}",
            page_type="event_detail",
            status="extracted",
            mapping_version_id_used=mapping_id,
            template_hash="stable",
        )
        await crud.upsert_extraction_baseline(
            db_session,
            source_id=source.id,
            page_id=page.id,
            mapping_version_id=mapping_id,
            record_id=None,
            baseline={"title": f"Event {idx}", "start_date": "2026-04-12", "source_url": page.url},
            field_stats={},
            dom_section_hash="stable",
            confidence_score=95,
        )
        await crud.create_record(
            db_session,
            source_id=source.id,
            record_type="event",
            page_id=page.id,
            source_url=page.url,
            title=None if idx < 2 else f"Event {idx}",
            start_date="2026-04-12",
            confidence_score=70,
            confidence_band="MEDIUM",
        )

    summary = await DriftDetectionService(db_session).analyze_source(source_id)
    assert summary["drift_rate"] > 20
    refreshed = await crud.get_source(db_session, source_id)
    assert refreshed is not None
    assert refreshed.queue_paused is True
    assert refreshed.status == "paused"


@pytest.mark.asyncio
async def test_drift_visibility_endpoints(test_client, db_session):
    source = await crud.create_source(db_session, url="https://drift-api-new.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        page_id=None,
        field_name="title",
        drift_type="FIELD_EMPTY",
        signal_type="field_empty",
        severity="high",
        sample_urls=["https://drift-api-new.test/event/1"],
    )

    all_resp = await test_client.get("/api/drift-signals", params={"source_id": source.id})
    assert all_resp.status_code == 200
    summary_resp = await test_client.get(f"/api/drift-summary/{source.id}")
    assert summary_resp.status_code == 200
    fields_resp = await test_client.get(f"/api/drift-fields/{source.id}")
    assert fields_resp.status_code == 200
    assert fields_resp.json()["fields"][0]["field_name"] == "title"


@pytest.mark.asyncio
async def test_recovery_workflow_ignore_and_remap(test_client, db_session):
    source = await crud.create_source(db_session, url="https://drift-recover.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping.status = "published"
    await db_session.commit()
    await crud.update_source(
        db_session,
        source.id,
        active_mapping_version_id=mapping.id,
        published_mapping_version_id=mapping.id,
    )
    signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="field_missing",
        drift_type="FIELD_MISSING",
        severity="high",
        sample_urls=["https://drift-recover.test/event/1"],
    )

    remap = await test_client.post(f"/api/sources/{source.id}/drift-signals/{signal.id}/remap-draft")
    assert remap.status_code == 200
    assert remap.json()["status"] == "draft_created"

    ignored = await test_client.post(
        f"/api/sources/{source.id}/drift-signals/{signal.id}/ignore",
        json={"resolution_notes": "false positive"},
    )
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "dismissed"
