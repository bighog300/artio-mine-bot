import json

import pytest
from sqlalchemy import select

from app.db import crud
from app.db.models import MappingDriftSignal, SourceMappingVersion
from app.source_mapper.drift_detection import DriftDetectionService


@pytest.mark.asyncio
async def test_drift_detection_emits_null_rate_and_new_family_signals(db_session):
    source = await crud.create_source(db_session, url="https://drift-phase6.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping.status = "approved"
    mapping.mapping_json = json.dumps({"family_rules": [{"family_key": "family:artists", "include": True}]})
    await db_session.commit()
    await crud.update_source(db_session, source.id, active_mapping_version_id=mapping.id, published_mapping_version_id=mapping.id)
    run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="queued", mapping_version_id=mapping.id)

    rows = []
    for idx in range(10):
        rows.append(
            {
                "url": f"https://drift-phase6.test/artists/{idx}",
                "normalized_url": f"https://drift-phase6.test/artists/{idx}",
                "mapping_version_id": mapping.id,
                "family_key": "family:artists",
                "status": "skipped",
                "skip_reason": "selector_miss" if idx < 6 else None,
                "last_refresh_outcome": "changed" if idx < 7 else "unchanged",
            }
        )
    for idx in range(6):
        rows.append(
            {
                "url": f"https://drift-phase6.test/new/{idx}",
                "normalized_url": f"https://drift-phase6.test/new/{idx}",
                "mapping_version_id": mapping.id,
                "family_key": "family:new-section",
                "status": "queued",
            }
        )
    await crud.upsert_crawl_frontier_rows(db_session, crawl_run_id=run.id, source_id=source.id, rows=rows)

    service = DriftDetectionService(db_session)
    result = await service.detect_for_source(source.id)
    assert result["created"] >= 3

    signals = await crud.list_mapping_drift_signals(db_session, source_id=source.id, status=None)
    signal_types = {s.signal_type for s in signals}
    assert "null_rate_spike" in signal_types
    assert "refresh_change_spike" in signal_types
    assert "new_unmapped_family" in signal_types


@pytest.mark.asyncio
async def test_drift_signal_dedupe_coalesces_equivalent_signal(db_session):
    source = await crud.create_source(db_session, url="https://drift-dedupe.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    first = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        family_key="family:a",
        signal_type="null_rate_spike",
        severity="medium",
        metrics={"null_rate": 0.4},
    )
    second = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        family_key="family:a",
        signal_type="null_rate_spike",
        severity="high",
        metrics={"null_rate": 0.8},
    )
    assert first.id == second.id
    assert second.severity == "high"


@pytest.mark.asyncio
async def test_mapping_health_derivation(db_session):
    source = await crud.create_source(db_session, url="https://drift-health.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    assert await crud.get_mapping_health_state(db_session, source_id=source.id, mapping_version_id=mapping.id) == "healthy"
    await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="refresh_change_spike",
        severity="medium",
    )
    assert await crud.get_mapping_health_state(db_session, source_id=source.id, mapping_version_id=mapping.id) == "warning"
    await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        signal_type="unexpected_skip_spike",
        severity="high",
        dedupe_hours=0,
    )
    assert await crud.get_mapping_health_state(db_session, source_id=source.id, mapping_version_id=mapping.id) == "stale"


@pytest.mark.asyncio
async def test_drift_api_status_actions_and_remap_draft(test_client, db_session):
    source = await crud.create_source(db_session, url="https://drift-api-phase6.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping.status = "published"
    mapping.mapping_json = json.dumps({"family_rules": [{"family_key": "family:a", "include": True}]})
    await db_session.commit()
    await crud.update_source(db_session, source.id, active_mapping_version_id=mapping.id, published_mapping_version_id=mapping.id)

    signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        family_key="family:a",
        signal_type="null_rate_spike",
        severity="high",
    )

    listed = await test_client.get(f"/api/sources/{source.id}/drift-signals", params={"status": "open"})
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == signal.id

    ack = await test_client.post(f"/api/sources/{source.id}/drift-signals/{signal.id}/acknowledge", json={})
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"

    resolved = await test_client.post(
        f"/api/sources/{source.id}/drift-signals/{signal.id}/resolve",
        json={"resolution_notes": "validated"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    open_signal = await crud.create_mapping_drift_signal(
        db_session,
        source_id=source.id,
        mapping_version_id=mapping.id,
        family_key="family:b",
        signal_type="new_unmapped_family",
        severity="medium",
        dedupe_hours=0,
    )
    remap = await test_client.post(f"/api/sources/{source.id}/drift-signals/{open_signal.id}/remap-draft")
    assert remap.status_code == 200
    payload = remap.json()
    assert payload["status"] == "draft_created"

    refreshed_source = await crud.get_source(db_session, source.id)
    assert refreshed_source is not None
    assert refreshed_source.active_mapping_version_id == mapping.id

    versions = list((await db_session.execute(select(SourceMappingVersion).where(SourceMappingVersion.source_id == source.id))).scalars().all())
    assert len(versions) == 2
    draft = next(v for v in versions if v.id != mapping.id)
    assert draft.status == "draft"

    tied_signal = await crud.get_mapping_drift_signal(db_session, source_id=source.id, signal_id=open_signal.id)
    assert tied_signal is not None
    assert tied_signal.mapping_version_id == mapping.id
