import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient):
    resp = await test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "db" in data
    assert "error:" not in data["db"]


@pytest.mark.asyncio
async def test_health_endpoint_does_not_leak_internal_error_text(test_client: AsyncClient):
    class _FailingSession:
        async def __aenter__(self):
            raise RuntimeError("sensitive-db-error")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with patch("app.db.database.AsyncSessionLocal", return_value=_FailingSession()):
        resp = await test_client.get("/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["db"] == "error"
    assert "sensitive-db-error" not in str(payload)


@pytest.mark.asyncio
async def test_create_source(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/sources", json={"url": "https://testsite.com", "name": "Test Site"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://testsite.com"
    assert data["name"] == "Test Site"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_source_duplicate(test_client: AsyncClient):
    await test_client.post("/api/sources", json={"url": "https://dup.com"})
    resp = await test_client.post("/api/sources", json={"url": "https://dup.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_sources(test_client: AsyncClient):
    await test_client.post("/api/sources", json={"url": "https://list1.com"})
    await test_client.post("/api/sources", json={"url": "https://list2.com"})
    resp = await test_client.get("/api/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_source(test_client: AsyncClient):
    create_resp = await test_client.post("/api/sources", json={"url": "https://get1.com"})
    source_id = create_resp.json()["id"]
    resp = await test_client.get(f"/api/sources/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == source_id


@pytest.mark.asyncio
async def test_get_source_not_found(test_client: AsyncClient):
    resp = await test_client.get("/api/sources/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_source(test_client: AsyncClient):
    create_resp = await test_client.post("/api/sources", json={"url": "https://del1.com"})
    source_id = create_resp.json()["id"]
    resp = await test_client.delete(f"/api/sources/{source_id}")
    assert resp.status_code == 204
    get_resp = await test_client.get(f"/api/sources/{source_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_stats(test_client: AsyncClient):
    resp = await test_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert "records" in data
    assert "pages" in data
    assert "total" in data["sources"]
    assert "by_type" in data["records"]


@pytest.mark.asyncio
async def test_list_records(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://records-test.com")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Test Artist",
        confidence_score=80,
        confidence_band="HIGH",
    )
    await db_session.commit()

    resp = await test_client.get("/api/records")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_approve_record(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://approve-test.com")
    record = await crud.create_record(
        db_session, source_id=source.id, record_type="artist", title="Artist to Approve"
    )
    await db_session.commit()

    resp = await test_client.post(f"/api/records/{record.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_record(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://reject-test.com")
    record = await crud.create_record(
        db_session, source_id=source.id, record_type="artist", title="Artist to Reject"
    )
    await db_session.commit()

    resp = await test_client.post(
        f"/api/records/{record.id}/reject", json={"reason": "Not relevant"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_bulk_approve(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://bulk-test.com")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="High Confidence",
        confidence_score=85,
        confidence_band="HIGH",
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Low Confidence",
        confidence_score=20,
        confidence_band="LOW",
    )
    await db_session.commit()

    resp = await test_client.post(
        "/api/records/bulk-approve",
        json={"source_id": source.id, "min_confidence": 70},
    )
    assert resp.status_code == 200
    assert resp.json()["approved_count"] == 1


@pytest.mark.asyncio
async def test_list_pages(test_client: AsyncClient):
    resp = await test_client.get("/api/pages")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data




def test_enqueue_pipeline_job_passes_job_id_as_function_argument():
    from app.api.routes import mine

    captured: dict[str, object] = {}

    class _FakeQueue:
        def enqueue(self, func_name: str, *args, **kwargs):
            captured["func_name"] = func_name
            captured["args"] = args
            captured["kwargs"] = kwargs
            return SimpleNamespace(id="rq-id-123")

    with patch("app.api.routes.mine.get_default_queue", return_value=_FakeQueue()):
        rq_job_id = mine._enqueue_pipeline_job("db-job-id", "source-1", "run_full_pipeline", {"k": "v"})

    assert rq_job_id == "rq-id-123"
    assert captured["func_name"] == "app.pipeline.runner.process_pipeline_job"
    assert captured["args"] == ("db-job-id", "source-1", "run_full_pipeline", {"k": "v"})
    assert captured["kwargs"] == {"job_timeout": mine.PIPELINE_JOB_TIMEOUT_SECONDS}

@pytest.mark.asyncio
async def test_mine_start(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-test.com"}
    )
    source_id = create_resp.json()["id"]

    with patch(
        "app.api.routes.mine._enqueue_pipeline_job",
        return_value="mock-rq-job-id",
    ):
        resp = await test_client.post(f"/api/mine/{source_id}/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("queued", "running", "pending")


@pytest.mark.asyncio
async def test_mine_start_sets_source_queued(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-queued.com"}
    )
    source_id = create_resp.json()["id"]

    with patch(
        "app.api.routes.mine._enqueue_pipeline_job",
        return_value="mock-rq-job-id",
    ):
        resp = await test_client.post(f"/api/mine/{source_id}/start")

    assert resp.status_code == 200
    source_resp = await test_client.get(f"/api/sources/{source_id}")
    assert source_resp.status_code == 200
    assert source_resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_mine_resume_chooses_extract_when_pages_pending_extraction(
    test_client: AsyncClient, db_session: AsyncSession
):
    source = await crud.create_source(
        db_session, url="https://resume-extract.com", name="Resume Extract"
    )
    await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://resume-extract.com/page-1",
        original_url="https://resume-extract.com/page-1",
        status="fetched",
    )

    with patch("app.api.routes.mine._enqueue_pipeline_job", return_value="rq-resume-extract"):
        resp = await test_client.post(f"/api/mine/{source.id}/resume")

    assert resp.status_code == 202
    assert "extract_page" in resp.json()["message"]


@pytest.mark.asyncio
async def test_mine_resume_chooses_crawl_for_paused_source_with_site_map(
    test_client: AsyncClient, db_session: AsyncSession
):
    source = await crud.create_source(db_session, url="https://resume-crawl.com")
    await crud.update_source(
        db_session,
        source.id,
        status="paused",
        site_map=json.dumps({"root_url": source.url, "sections": []}),
    )

    with patch("app.api.routes.mine._enqueue_pipeline_job", return_value="rq-resume-crawl"):
        resp = await test_client.post(f"/api/mine/{source.id}/resume")

    assert resp.status_code == 202
    assert "crawl_section" in resp.json()["message"]


@pytest.mark.asyncio
async def test_mining_status_includes_queued_job(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-status-queued.com"}
    )
    source_id = create_resp.json()["id"]

    with patch(
        "app.api.routes.mine._enqueue_pipeline_job",
        return_value="mock-rq-job-id",
    ):
        await test_client.post(f"/api/mine/{source_id}/start")

    status_resp = await test_client.get(f"/api/mine/{source_id}/status")
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload["status"] == "queued"
    assert payload["current_job"] is not None
    assert payload["current_job"]["status"] == "queued"


@pytest.mark.asyncio
async def test_mine_start_not_found(test_client: AsyncClient):
    resp = await test_client.post("/api/mine/nonexistent/start")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mine_start_returns_controlled_error_when_enqueue_fails(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-enqueue-fail.com"}
    )
    source_id = create_resp.json()["id"]

    with (
        patch("app.api.routes.mine._assert_queue_available"),
        patch("app.api.routes.mine._enqueue_pipeline_job", side_effect=RuntimeError("redis down")),
    ):
        resp = await test_client.post(f"/api/mine/{source_id}/start")

    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert any(
        message in detail
        for message in (
            "Redis queue unavailable",
            "queue infrastructure unavailable",
        )
    )

    source_resp = await test_client.get(f"/api/sources/{source_id}")
    assert source_resp.status_code == 200
    assert source_resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_queue_health_endpoint(test_client: AsyncClient):
    with patch(
        "app.api.routes.mine.check_queue_health",
        return_value=SimpleNamespace(redis_ok=True, workers_available=True, worker_count=1),
    ):
        resp = await test_client.get("/api/mine/queue/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["redis_ok"] is True
    assert payload["workers_available"] is True
    assert payload["worker_count"] == 1


@pytest.mark.asyncio
async def test_export_preview(test_client: AsyncClient):
    resp = await test_client.get("/api/export/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert "record_count" in data
    assert "artio_configured" in data
    assert "by_type" in data


@pytest.mark.asyncio
async def test_list_images(test_client: AsyncClient):
    resp = await test_client.get("/api/images")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_settings_openai_api_key_flow(test_client: AsyncClient):
    read_resp = await test_client.get("/api/settings")
    assert read_resp.status_code == 200
    assert "openai_api_key_masked" in read_resp.json()
    assert "openai_configured" in read_resp.json()

    save_resp = await test_client.post("/api/settings", json={"openai_api_key": "sk-test-openai-1234"})
    assert save_resp.status_code == 400
    assert "deployment-managed" in save_resp.json()["detail"]


@pytest.mark.asyncio
async def test_settings_save_returns_handled_error_when_env_persist_fails(test_client: AsyncClient):
    save_resp = await test_client.post(
        "/api/settings",
        json={"max_crawl_depth": 5, "max_pages_per_source": 1000, "crawl_delay_ms": 250},
    )
    assert save_resp.status_code == 200
    payload = save_resp.json()
    assert payload["max_crawl_depth"] == 5
    assert payload["max_pages_per_source"] == 1000
    assert payload["crawl_delay_ms"] == 250


@pytest.mark.asyncio
async def test_settings_rejects_out_of_range_runtime_values(test_client: AsyncClient):
    resp = await test_client.post("/api/settings", json={"max_crawl_depth": 0})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_artists_endpoint(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://search-artists.com")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alice Elahi",
        bio="Contemporary artist",
        completeness_score=82,
        has_conflicts=False,
        raw_data=json.dumps({"artist_payload": {"exhibitions": [{"title": "Solo Show"}], "articles": []}}),
    )

    resp = await test_client.get("/api/search/artists", params={"q": "Alice", "has_exhibitions": "true"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["name"] == "Alice Elahi"


@pytest.mark.asyncio
async def test_graph_artist_endpoint(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://graph-artist.com")
    exhibition = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="exhibition",
        title="Museum Night",
    )
    article = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist_article",
        title="Interview with Nora",
    )
    artist = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Nora Artist",
        raw_data=json.dumps(
            {
                "artist_payload": {
                    "exhibitions": [{"title": exhibition.title}],
                    "articles": [{"title": article.title}],
                }
            }
        ),
    )

    resp = await test_client.get(f"/api/graph/artist/{artist.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["artist"]["id"] == artist.id
    assert any(item["id"] == exhibition.id for item in payload["exhibitions"])
    assert any(item["id"] == article.id for item in payload["articles"])


@pytest.mark.asyncio
async def test_export_artists_clean_endpoint(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://export-artist.com")
    artist = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Export Artist",
        bio="Bio",
        raw_data=json.dumps(
            {
                "artist_payload": {
                    "exhibitions": [{"title": "Show"}],
                    "articles": [{"title": "Profile"}],
                },
                "provenance": {"artist_name": {"value": "Export Artist"}},
            }
        ),
    )

    list_resp = await test_client.get("/api/export/artists")
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["total"] >= 1
    assert "provenance" not in list_payload["items"][0]

    detail_resp = await test_client.get(f"/api/export/artists/{artist.id}", params={"include_provenance": "true"})
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload["artist_name"] == "Export Artist"
    assert "provenance" in detail_payload


@pytest.mark.asyncio
async def test_metrics_endpoint(test_client: AsyncClient):
    resp = await test_client.get("/api/metrics")
    assert resp.status_code == 200
    payload = resp.json()
    assert "total_artists" in payload
    assert "avg_completeness" in payload
    assert "conflicts_count" in payload


@pytest.mark.asyncio
async def test_legacy_metrics_endpoint_not_exposed(test_client: AsyncClient):
    resp = await test_client.get("/metrics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_semantic_artist_search_returns_ranked_results(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://semantic-artists.com")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alice Painter",
        bio="Contemporary painter exploring memory and color fields in Cape Town",
        city="Cape Town",
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Bruno Sculptor",
        bio="Large scale bronze sculpture in Johannesburg",
        city="Johannesburg",
    )

    resp = await test_client.get("/api/semantic/artists", params={"q": "memory painter cape town"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 2
    assert payload["items"][0]["name"] == "Alice Painter"
    assert payload["items"][0]["semantic_score"] >= payload["items"][1]["semantic_score"]


@pytest.mark.asyncio
async def test_duplicate_suggestions_and_merge(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://duplicates.com")
    first = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alice Elahi",
        bio="Cape Town contemporary artist working across painting",
        website_url="https://alice.example.com",
        raw_data=json.dumps({"related": {"exhibitions": [{"title": "City Light"}]}}),
    )
    second = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alice N. Elahi",
        bio="Contemporary painter from Cape Town with city light exhibitions",
        website_url="https://alice.example.com",
        raw_data=json.dumps({"related": {"exhibitions": [{"title": "City Light"}]}}),
    )

    dup_resp = await test_client.get("/api/suggest/duplicates", params={"min_score": 0.55})
    assert dup_resp.status_code == 200
    dup_payload = dup_resp.json()
    assert dup_payload["total"] >= 1
    pair_ids = {(item["left_id"], item["right_id"]) for item in dup_payload["items"]}
    assert (first.id, second.id) in pair_ids or (second.id, first.id) in pair_ids

    merge_resp = await test_client.post(
        "/api/merge/artists",
        json={"primary_id": first.id, "secondary_id": second.id},
    )
    assert merge_resp.status_code == 200
    assert merge_resp.json()["status"] == "merged"

    get_secondary = await test_client.get(f"/api/records/{second.id}")
    assert get_secondary.status_code == 404


@pytest.mark.asyncio
async def test_related_artists_and_ask_endpoint(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://related.com")
    anchor = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alice Elahi",
        bio="Artist focused on abstract memory and color",
        city="Cape Town",
        raw_data=json.dumps({"related": {"exhibitions": [{"title": "Harbor Echoes"}]}}),
    )
    peer = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alicia Elahi",
        bio="Abstract color painter exploring memory",
        city="Cape Town",
        raw_data=json.dumps({"related": {"exhibitions": [{"title": "Harbor Echoes"}]}}),
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Jonas Metal",
        bio="Steel installation artist",
        city="Durban",
    )

    related_resp = await test_client.get(f"/api/related/artists/{anchor.id}")
    assert related_resp.status_code == 200
    related_payload = related_resp.json()
    assert related_payload["items"]
    assert related_payload["items"][0]["id"] == peer.id

    ask_resp = await test_client.post(
        "/api/ask",
        json={"query": "Show me artists similar to Alice Elahi who exhibited in Cape Town"},
    )
    assert ask_resp.status_code == 200
    ask_payload = ask_resp.json()
    assert ask_payload["results"]
    assert ask_payload["intent"] in {"artist_similarity", "semantic_lookup"}


@pytest.mark.asyncio
async def test_analyze_source_structure_endpoint_cached(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(
        db_session,
        url="https://cached-structure.com",
        name="Cached",
    )
    await crud.update_source(
        db_session,
        source.id,
        structure_status="analyzed",
        structure_map=json.dumps({"crawl_targets": [], "mining_map": {}}),
    )

    resp = await test_client.post(f"/api/sources/{source.id}/analyze-structure")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "cached"
    assert "structure" in payload


@pytest.mark.asyncio
async def test_analyze_source_structure_endpoint_runs_analysis(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://analyze-structure.com", "name": "Analyze"}
    )
    source_id = create_resp.json()["id"]

    fake_fetch = SimpleNamespace(html="<html><nav><a href='/artists'>Artists</a></nav></html>", error=None)
    structure_payload = {
        "crawl_targets": [{"url_pattern": "/artists/[letter]", "estimated_pages": 26}],
        "mining_map": {"artist_profile": {"url_pattern": "/artists/[letter]/[name]", "expected_fields": ["name", "bio"]}},
    }

    with patch("app.crawler.fetcher.fetch", new=AsyncMock(return_value=fake_fetch)):
        with patch("app.crawler.site_structure_analyzer.analyze_structure", new=AsyncMock(return_value=structure_payload)):
            resp = await test_client.post(f"/api/sources/{source_id}/analyze-structure")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "analyzed"
    assert payload["structure"]["crawl_targets"][0]["url_pattern"] == "/artists/[letter]"


@pytest.mark.asyncio
async def test_create_and_list_backfill_schedule(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/backfill/schedules",
        json={
            "name": "Weekly Artist Refresh",
            "schedule_type": "recurring",
            "cron_expression": "0 2 * * 0",
            "filters": {"record_type": "artist", "min_completeness": 0, "max_completeness": 70},
            "options": {"limit": 10},
            "auto_start": False,
        },
    )
    assert create_resp.status_code == 200
    payload = create_resp.json()
    assert payload["name"] == "Weekly Artist Refresh"
    assert payload["cron_expression"] == "0 2 * * 0"

    list_resp = await test_client.get("/api/backfill/schedules")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    assert any(item["id"] == payload["id"] for item in data["items"])


@pytest.mark.asyncio
async def test_create_backfill_schedule_invalid_cron(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/backfill/schedules",
        json={
            "name": "Bad Cron",
            "schedule_type": "recurring",
            "cron_expression": "not a cron",
            "filters": {},
            "options": {},
        },
    )
    assert resp.status_code == 400
