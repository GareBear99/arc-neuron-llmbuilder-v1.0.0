import pytest
import httpx
from tests._client import make_transport
from arc.services.bootstrap import seed_demo


def setup_module():
    seed_demo()


@pytest.mark.anyio
async def test_blueprint_calibration_and_heatmap():
    async with httpx.AsyncClient(transport=make_transport(), base_url='http://testserver') as client:
        structures = (await client.get('/api/geo/structures')).json()['structures']
        structure_id = structures[0]['structure_id']
        bp = await client.post('/api/geo/blueprints', json={
            'structure_id': structure_id,
            'name': 'Test Overlay',
            'image_url': 'https://example.local/test.png'
        }, headers={'X-ARC-Role':'analyst'})
        cal = await client.post('/api/geo/calibrations', json={
            'structure_id': structure_id,
            'name': 'Lab Profile',
            'path_loss': 2.4,
            'noise_db': 4.0,
            'smoothing': 0.7,
        }, headers={'X-ARC-Role':'analyst'})
        heat = await client.get(f'/api/geo/heatmap/{structure_id}?grid_size=6')
    assert bp.status_code == 200
    assert cal.status_code == 200
    assert heat.status_code == 200
    body = heat.json()
    assert body['structure_id'] == structure_id
    assert any('count' in cell for cell in body['cells'])


@pytest.mark.anyio
async def test_import_evidence_and_receipts():
    async with httpx.AsyncClient(transport=make_transport(), base_url='http://testserver') as client:
        structures = (await client.get('/api/geo/structures')).json()['structures']
        structure_id = structures[0]['structure_id']
        imported = await client.post('/api/geo/import-tracks', json={
            'subject': 'Imported Device',
            'structure_id': structure_id,
            'source': 'json-import',
            'track_points': [
                {'lat': structures[0]['center']['lat'], 'lng': structures[0]['center']['lng'], 'confidence': 0.91},
                {'lat': structures[0]['center']['lat'] + 0.00001, 'lng': structures[0]['center']['lng'] + 0.00001, 'confidence': 0.89}
            ]
        }, headers={'X-ARC-Role':'observer'})
        incident = await client.post('/api/incidents', json={
            'title': 'Imported signal burst',
            'severity': 'high',
            'status': 'open',
            'subject': 'Imported Device',
            'structure_id': structure_id,
            'details': {'source': 'json-import'}
        }, headers={'X-ARC-Role':'analyst'})
        evidence = await client.get('/api/evidence?subject=Imported%20Device')
        verify = await client.get('/api/receipts/verify')
    assert imported.status_code == 200
    assert incident.status_code == 200
    assert evidence.status_code == 200
    assert verify.status_code == 200
    assert evidence.json()['subject'] == 'Imported Device'
    assert evidence.json()['tracks']
    assert verify.json()['ok'] is True
