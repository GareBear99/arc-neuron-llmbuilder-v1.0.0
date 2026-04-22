from __future__ import annotations

from fastapi.testclient import TestClient

from arc_lang.api.app import app
from arc_lang.api.routers import acquisition_router, core_router, knowledge_router, runtime_router
from arc_lang.core.db import init_db
from arc_lang.services.backend_diagnostics import get_translation_readiness_matrix
from arc_lang.services.seed_ingest import ingest_common_seed


client = TestClient(app)


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_router_surface_is_split_into_domain_groups():
    grouped_counts = {
        'core': len(core_router.routes),
        'runtime': len(runtime_router.routes),
        'knowledge': len(knowledge_router.routes),
        'acquisition': len(acquisition_router.routes),
    }
    assert grouped_counts['core'] >= 10
    assert grouped_counts['runtime'] >= 10
    assert grouped_counts['knowledge'] >= 10
    assert grouped_counts['acquisition'] >= 4


def test_health_route_reports_current_version():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['version'] == '0.27.0'


def test_translation_readiness_matrix_skips_identity_pairs_for_non_identity_backends():
    result = get_translation_readiness_matrix(target_language_id='lang:eng', provider_name='argos_local', limit=10)
    assert result['ok'] is True
    assert all(not (row['source_language_id'] == 'lang:eng' and row['target_language_id'] == 'lang:eng') for row in result['rows'])
