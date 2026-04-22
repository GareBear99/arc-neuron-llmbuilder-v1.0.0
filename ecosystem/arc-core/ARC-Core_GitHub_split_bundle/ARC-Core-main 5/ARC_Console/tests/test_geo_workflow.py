import pytest
import httpx
from tests._client import make_transport
from arc.services.bootstrap import seed_demo


def setup_module():
    seed_demo()


@pytest.mark.anyio
async def test_geo_seed_and_demo_track():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        structures = (await client.get('/api/geo/structures')).json()['structures']
        assert structures
        structure_id = structures[0]['structure_id']
        sensors = (await client.get(f'/api/geo/sensors?structure_id={structure_id}')).json()['sensors']
        assert len(sensors) >= 5
        result = await client.post(f'/api/geo/demo-track/{structure_id}', headers={'X-ARC-Role':'observer'})
    assert result.status_code == 200
    body = result.json()
    assert body['confidence'] >= 0.15
    assert 'zone' in body


@pytest.mark.anyio
async def test_manual_geo_estimate_and_geofence():
    async with httpx.AsyncClient(transport=make_transport(), base_url="http://testserver") as client:
        structure = (await client.get('/api/geo/structures')).json()['structures'][0]
        structure_id = structure['structure_id']
        sensors = (await client.get(f'/api/geo/sensors?structure_id={structure_id}')).json()['sensors']
        geofence = await client.post('/api/geo/geofences', json={'name':'Test Fence','geofence_type':'restricted','structure_id':structure_id,'polygon':structure['polygon'],'severity':8}, headers={'X-ARC-Role':'analyst'})
        observations = [{'sensor_id': s['sensor_id'], 'rssi': -55.0 + idx, 'reliability': s['reliability']} for idx, s in enumerate(sensors[:4])]
        res = await client.post('/api/geo/estimate', json={'subject':'Tracked Phone','structure_id':structure_id,'source':'test-rf','observations':observations}, headers={'X-ARC-Role':'observer'})
    assert geofence.status_code == 200
    assert res.status_code == 200
    body = res.json()
    assert body['sensor_count'] == len(observations)
    assert len(body['geofence_hits']) >= 1
