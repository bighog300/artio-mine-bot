import pytest

from app.db import crud
from app.source_mapper.auto_repair import AutoRepairService


async def _seed_mapping_with_pages(db_session):
    source = await crud.create_source(db_session, url="https://repair-phase65.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping.status = "published"
    await db_session.commit()
    await crud.update_source(
        db_session,
        source.id,
        active_mapping_version_id=mapping.id,
        published_mapping_version_id=mapping.id,
    )
    page_type = await crud.create_source_mapping_page_type(db_session, mapping.id, key="event_detail", label="Event")
    await crud.create_source_mapping_row(
        db_session,
        mapping.id,
        page_type_id=page_type.id,
        selector=".old-title",
        sample_value="Old",
        destination_entity="event",
        destination_field="title",
        status="approved",
    )

    urls = []
    for idx in range(8):
        url = f"https://repair-phase65.test/event/{idx}"
        urls.append(url)
        await crud.create_page(
            db_session,
            source.id,
            url,
            page_type="event_detail",
            mapping_version_id_used=mapping.id,
            status="extracted",
            html=f"<html><body><h1 class='title-new'>Event {idx}</h1></body></html>",
        )
    return source, mapping, urls


@pytest.mark.asyncio
async def test_selector_break_generates_repair_proposal(db_session):
    source, mapping, urls = await _seed_mapping_with_pages(db_session)
    signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="selector_fail",
        drift_type="SELECTOR_FAIL",
        severity="high",
        field_name="title",
        mapping_field="title",
        failing_selector=".old-title",
        sample_urls=urls,
        dedupe_hours=0,
    )

    proposals = await AutoRepairService(db_session).generate_for_signal(signal)
    assert proposals
    assert proposals[0].field_name == "title"


@pytest.mark.asyncio
async def test_proposal_validation_success(db_session):
    source, mapping, urls = await _seed_mapping_with_pages(db_session)
    signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="field_empty",
        drift_type="FIELD_EMPTY",
        severity="high",
        field_name="title",
        mapping_field="title",
        failing_selector=".old-title",
        sample_urls=urls,
        dedupe_hours=0,
    )
    proposals = await AutoRepairService(db_session).generate_for_signal(signal)
    validated = [p for p in proposals if p.status == "VALIDATED"]
    assert validated


@pytest.mark.asyncio
async def test_proposal_rejected_on_poor_match(db_session):
    source, mapping, urls = await _seed_mapping_with_pages(db_session)
    signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="field_empty",
        drift_type="FIELD_EMPTY",
        severity="high",
        field_name="year",
        mapping_field="year",
        failing_selector=".old-year",
        sample_urls=urls,
        dedupe_hours=0,
    )
    proposals = await AutoRepairService(db_session).generate_for_signal(signal)
    assert proposals
    assert any(p.status == "REJECTED" for p in proposals)


@pytest.mark.asyncio
async def test_safe_mapping_version_creation_and_no_regression(db_session):
    source, mapping, urls = await _seed_mapping_with_pages(db_session)
    signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="selector_fail",
        drift_type="SELECTOR_FAIL",
        severity="high",
        field_name="title",
        mapping_field="title",
        failing_selector=".old-title",
        sample_urls=urls,
        dedupe_hours=0,
    )
    proposals = await AutoRepairService(db_session).generate_for_signal(signal)
    proposal = next(p for p in proposals if p.status in {"DRAFT", "VALIDATED"})

    applied_mapping_id = await AutoRepairService(db_session).apply_proposal(source.id, proposal.id, reviewed_by="tester")
    assert applied_mapping_id != mapping.id

    original_rows = await crud.list_source_mapping_rows(db_session, source.id, mapping.id, skip=0, limit=50)
    new_rows = await crud.list_source_mapping_rows(db_session, source.id, applied_mapping_id, skip=0, limit=50)
    assert any(r.selector == ".old-title" for r in original_rows)
    assert any(r.selector != ".old-title" and r.destination_field == "title" for r in new_rows)


@pytest.mark.asyncio
async def test_mapping_repair_api_endpoints(test_client, db_session):
    source, mapping, _urls = await _seed_mapping_with_pages(db_session)
    proposal = await crud.create_mapping_repair_proposal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        field_name="title",
        old_selector=".old-title",
        proposed_selector=".title-new",
        confidence_score=0.92,
        supporting_pages=["https://repair-phase65.test/event/0"],
        drift_signals_used=[],
        validation_results={"success_rate": 1.0, "valid_value_rate": 1.0, "sample_size": 1},
        status="VALIDATED",
    )

    listed = await test_client.get("/api/mapping-repair-proposals", params={"source_id": source.id})
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == proposal.id

    approved = await test_client.post(f"/api/mapping-repair/{proposal.id}/approve", params={"source_id": source.id})
    assert approved.status_code == 200
    assert approved.json()["status"] == "VALIDATED"

    applied = await test_client.post(f"/api/mapping-repair/{proposal.id}/apply", params={"source_id": source.id})
    assert applied.status_code == 200
    assert applied.json()["status"] == "APPLIED"

    rejected = await crud.create_mapping_repair_proposal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        field_name="year",
        old_selector=".old-year",
        proposed_selector=".year-new",
        confidence_score=0.2,
        supporting_pages=[],
        drift_signals_used=[],
        validation_results={"success_rate": 0.2, "valid_value_rate": 0.2, "sample_size": 5},
        status="DRAFT",
    )
    rejected_resp = await test_client.post(f"/api/mapping-repair/{rejected.id}/reject", params={"source_id": source.id})
    assert rejected_resp.status_code == 200
    assert rejected_resp.json()["status"] == "REJECTED"
