import json
from pathlib import Path
import pytest
import httpx
from tests._client import make_transport
from arc.services.bootstrap import seed_demo
from arc.core.config import AUTH_BOOTSTRAP_PASSWORD


def setup_module():
    seed_demo()


@pytest.mark.anyio
async def test_auth_login_and_session():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        login = await client.post('/api/auth/login', json={'username':'admin','password':AUTH_BOOTSTRAP_PASSWORD,'source':'test-suite'})
        assert login.status_code == 200
        token = login.json()['token']
        session = await client.get('/api/auth/session', headers={'Authorization': f'Bearer {token}'})
    assert session.status_code == 200
    assert session.json()['session']['role'] == 'admin'


@pytest.mark.anyio
async def test_connector_poll_and_signed_receipts_and_notes():
    temp_dir = Path('/mnt/data/arc_v6_connector_test')
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / '0002_feed.jsonl').write_text(json.dumps({
        'event_type':'arrival','source':'connector-test','subject':'Connector Subject','location':'Ops Room','confidence':0.88,'severity':7
    }) + '\n', encoding='utf-8')
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        login = await client.post('/api/auth/login', json={'username':'admin','password':AUTH_BOOTSTRAP_PASSWORD,'source':'test-suite'})
        token = login.json()['token']
        conn = await client.post('/api/connectors', json={'name':'test-feed','connector_type':'filesystem_jsonl','path':str(temp_dir),'enabled':True}, headers={'X-ARC-Role':'admin'})
        connector_id = conn.json()['connector_id']
        polled = await client.post(f'/api/connectors/{connector_id}/poll', headers={'X-ARC-Role':'admin'})
        events = await client.get('/api/events?q=Connector Subject')
        note = await client.post('/api/notes', json={'subject_type':'subject','subject_id':'Connector Subject','title':'Analyst note','body':'validated feed','tags':['feed','validated']}, headers={'X-ARC-Role':'analyst'})
        evidence = await client.get('/api/evidence?subject=Connector%20Subject')
        verify = await client.get('/api/receipts/verify')
    assert polled.status_code == 200
    assert polled.json()['imported'] >= 1
    assert events.status_code == 200
    assert events.json()['events']
    assert note.status_code == 200
    assert evidence.status_code == 200
    assert evidence.json()['summary']['note_count'] >= 1
    assert verify.json()['ok'] is True
