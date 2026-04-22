import pytest
import httpx
from tests._client import make_transport
from arc.services.bootstrap import seed_demo


def setup_module():
    seed_demo()


@pytest.mark.anyio
async def test_event_search_pushdown_and_health_version():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        health = await client.get("/health")
        search = await client.get("/api/events?q=meeting&limit=5")
    assert health.status_code == 200
    assert health.json()["version"] == "6.0.0"
    assert any(evt["event_type"] == "meeting" for evt in search.json()["events"])


@pytest.mark.anyio
async def test_case_attach_deduplicates_same_event():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        case = await client.post("/api/cases", json={"title":"Dedup Case","priority":"high","summary":"test","status":"open"}, headers={"X-ARC-Role":"analyst"})
        case_id = case.json()["case_id"]
        event_id = (await client.get("/api/events?limit=1")).json()["events"][0]["id"]
        first = await client.post(f"/api/cases/{case_id}/attach/{event_id}", headers={"X-ARC-Role":"analyst"})
        second = await client.post(f"/api/cases/{case_id}/attach/{event_id}", headers={"X-ARC-Role":"analyst"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["events"]) == 1


@pytest.mark.anyio
async def test_blueprint_and_calibration_upsert_stable_identity():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        structures = (await client.get("/api/geo/structures")).json()["structures"]
        structure_id = structures[0]["structure_id"]
        first = await client.post("/api/geo/blueprints", json={"structure_id": structure_id, "name": "Stable Overlay", "image_url": "https://example.local/a.png"}, headers={"X-ARC-Role":"analyst"})
        second = await client.post("/api/geo/blueprints", json={"structure_id": structure_id, "name": "Stable Overlay", "image_url": "https://example.local/b.png"}, headers={"X-ARC-Role":"analyst"})
        cal1 = await client.post("/api/geo/calibrations", json={"structure_id": structure_id, "name": "Stable Cal", "path_loss": 2.2, "noise_db": 3.5, "smoothing": 0.4}, headers={"X-ARC-Role":"analyst"})
        cal2 = await client.post("/api/geo/calibrations", json={"structure_id": structure_id, "name": "Stable Cal", "path_loss": 2.8, "noise_db": 4.5, "smoothing": 0.5}, headers={"X-ARC-Role":"analyst"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["overlay_id"] == second.json()["overlay_id"]
    assert second.json()["image_url"] == "https://example.local/b.png"
    assert cal1.json()["profile_id"] == cal2.json()["profile_id"]
    assert cal2.json()["profile"]["path_loss"] == 2.8
