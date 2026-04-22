import pytest
import httpx
from tests._client import make_transport
from arc.services.bootstrap import seed_demo


def setup_module():
    seed_demo()


@pytest.mark.anyio
async def test_health():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


@pytest.mark.anyio
async def test_event_and_graph():
    payload = {
        "event_type": "meeting",
        "source": "test",
        "subject": "Test Subject",
        "object": "Test Object",
        "location": "Test Ave",
        "confidence": 0.9,
        "severity": 8,
        "payload": {"x": 1},
    }
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        res = await client.post("/api/events", json=payload, headers={"X-ARC-Role":"observer"})
        graph = await client.get("/api/graph")
    assert res.status_code == 200
    graph_body = graph.json()
    assert len(graph_body["nodes"]) >= 2
    assert len(graph_body["edges"]) >= 1


@pytest.mark.anyio
async def test_case_workflow():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        case = await client.post("/api/cases", json={"title":"Workflow Case","priority":"high","summary":"test","status":"open"}, headers={"X-ARC-Role":"analyst"})
        case_id = case.json()["case_id"]
        events = (await client.get("/api/events")).json()["events"]
        attached = await client.post(f"/api/cases/{case_id}/attach/{events[0]['id']}", headers={"X-ARC-Role":"analyst"})
    assert case.status_code == 200
    assert attached.status_code == 200
    assert len(attached.json()["events"]) >= 1


@pytest.mark.anyio
async def test_proposal_approval():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        entities = (await client.get("/api/entities")).json()["entities"]
        target = entities[0]["entity_id"]
        prop = await client.post("/api/proposals", json={"action":"observe","target_type":"entity","target_id":target,"rationale":"test","simulation_depth":2}, headers={"X-ARC-Role":"operator"})
        pid = prop.json()["proposal_id"]
        approved = await client.post(f"/api/proposals/{pid}/approve", headers={"X-ARC-Role":"approver"})
    assert prop.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
