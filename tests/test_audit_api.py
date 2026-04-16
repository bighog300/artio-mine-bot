from app.db import crud


async def test_audit_events_list_and_detail(test_client, db_session):
    event = await crud.create_audit_event(
        db_session,
        event_type="update",
        entity_type="record",
        entity_id="rec-1",
        user_id="admin",
        user_name="Admin",
        message="Updated record",
        changes={"before": {"title": "Old"}, "after": {"title": "New"}},
        metadata={"reason": "manual"},
    )

    response = await test_client.get("/api/audit/events", params={"event_type": "update", "search": "Updated"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == event.id

    detail = await test_client.get(f"/api/audit/events/{event.id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["id"] == event.id
    assert detail_payload["changes"]["after"]["title"] == "New"


async def test_audit_events_export_csv(test_client, db_session):
    await crud.create_audit_event(
        db_session,
        event_type="create",
        entity_type="source",
        entity_id="source-1",
        user_id="system",
        message="Created source",
    )

    response = await test_client.get("/api/audit/events/export")
    assert response.status_code == 200
    assert "id,timestamp,event_type,entity_type" in response.text
    assert "create,source,source-1" in response.text
