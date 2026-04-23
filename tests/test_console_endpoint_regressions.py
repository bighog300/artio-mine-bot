from httpx import AsyncClient


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
