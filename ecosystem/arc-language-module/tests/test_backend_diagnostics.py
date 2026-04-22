from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.governance import set_language_capability
from arc_lang.core.models import CapabilityUpdateRequest
from arc_lang.services.backend_diagnostics import get_provider_diagnostics, get_translation_pair_readiness, get_translation_readiness_matrix
from arc_lang.services.provider_registry import register_provider, set_provider_health


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_argos_provider_diagnostics_are_honest():
    res = get_provider_diagnostics('argos_local')
    assert res['ok'] is True
    assert res['provider_name'] == 'argos_local'
    assert res['readiness'] in {'ready', 'degraded', 'blocked'}
    assert 'dependency' in res


def test_translation_pair_readiness_for_local_seed():
    res = get_translation_pair_readiness('lang:spa', 'lang:eng', provider_name='local_seed')
    assert res['ok'] is True
    assert res['best_provider']['provider_name'] == 'local_seed'
    assert res['best_provider']['readiness'] == 'ready'


def test_translation_pair_readiness_for_boundary_stub_is_theoretical_when_healthy():
    register_provider('nllb_bridge', 'translation', enabled=True, local_only=False, notes='future bridge')
    set_provider_health('nllb_bridge', 'healthy', latency_ms=200, error_rate=0.01, notes='reachable boundary')
    set_language_capability(CapabilityUpdateRequest(language_id='lang:fra', capability_name='translation', maturity='experimental', confidence=0.71, provider='nllb_bridge', notes='future bridge'))
    set_language_capability(CapabilityUpdateRequest(language_id='lang:eng', capability_name='translation', maturity='experimental', confidence=0.71, provider='nllb_bridge', notes='future bridge'))
    res = get_translation_pair_readiness('lang:fra', 'lang:eng', provider_name='nllb_bridge')
    assert res['ok'] is True
    assert res['best_provider']['provider_name'] == 'nllb_bridge'
    assert res['best_provider']['readiness'] in {'theoretical', 'blocked'}


def test_translation_readiness_matrix_returns_rows():
    res = get_translation_readiness_matrix(target_language_id='lang:eng', limit=10)
    assert res['ok'] is True
    assert any(r['target_language_id'] == 'lang:eng' for r in res['rows'])
