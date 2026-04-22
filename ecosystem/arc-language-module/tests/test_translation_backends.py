from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.governance import set_language_capability
from arc_lang.services.orchestration import route_runtime_translation
from arc_lang.services.translation_backends import list_builtin_translation_backends
from arc_lang.core.models import CapabilityUpdateRequest, RuntimeTranslateRequest
from arc_lang.services.provider_registry import set_provider_health


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_builtin_translation_backends_listed():
    res = list_builtin_translation_backends()
    names = {b['provider_name'] for b in res['backends']}
    assert {'local_seed', 'mirror_mock', 'argos_local', 'argos_bridge', 'nllb_bridge'} <= names


def test_runtime_translation_uses_backend_adapter_local_seed():
    result = route_runtime_translation(RuntimeTranslateRequest(text='hola', target_language_id='lang:eng'))
    assert result['ok'] is True
    assert result['backend']['provider'] == 'local_seed'
    assert result['backend']['mode'] == 'backend_local_seed'
    assert result['translation']['translated_text'] == 'hello'


def test_runtime_translation_mirror_backend_same_language():
    set_language_capability(CapabilityUpdateRequest(language_id='lang:eng', capability_name='translation', maturity='reviewed', confidence=0.9, provider='mirror_mock', notes='same-language test backend'))
    result = route_runtime_translation(RuntimeTranslateRequest(text='hello', source_language_id='lang:eng', target_language_id='lang:eng', preferred_translation_provider='mirror_mock'))
    assert result['ok'] is True
    assert result['backend']['provider'] == 'mirror_mock'
    assert result['translation']['translated_text'] == 'hello'


def test_runtime_translation_argos_local_honest_when_dependency_missing_or_unconfigured():
    set_language_capability(CapabilityUpdateRequest(language_id='lang:spa', capability_name='translation', maturity='experimental', confidence=0.72, provider='argos_local', notes='optional local argos backend'))
    set_language_capability(CapabilityUpdateRequest(language_id='lang:eng', capability_name='translation', maturity='experimental', confidence=0.72, provider='argos_local', notes='optional local argos backend'))
    result = route_runtime_translation(RuntimeTranslateRequest(text='hola mundo', source_language_id='lang:spa', target_language_id='lang:eng', preferred_translation_provider='argos_local', dry_run=False))
    if result['ok']:
        assert result['backend']['provider'] == 'argos_local'
        assert result['backend']['mode'] == 'backend_argos_local'
    else:
        assert result['error'] in {'translation_backend_dependency_missing', 'translation_backend_language_pair_missing', 'translation_backend_runtime_failed', 'translation_backend_dependency_failed', 'translation_backend_language_code_unmapped'}


def test_runtime_translation_boundary_stub_dry_run():
    set_language_capability(CapabilityUpdateRequest(language_id='lang:fra', capability_name='translation', maturity='experimental', confidence=0.71, provider='nllb_bridge', notes='future external bridge'))
    set_language_capability(CapabilityUpdateRequest(language_id='lang:eng', capability_name='translation', maturity='experimental', confidence=0.71, provider='nllb_bridge', notes='future external bridge'))
    set_provider_health('nllb_bridge', 'healthy', latency_ms=180, error_rate=0.01, notes='dry-run reachable')
    result = route_runtime_translation(RuntimeTranslateRequest(text='bonjour', source_language_id='lang:fra', target_language_id='lang:eng', preferred_translation_provider='nllb_bridge'))
    assert result['ok'] is True
    assert result['backend']['provider'] == 'nllb_bridge'
    assert result['backend']['mode'] == 'backend_boundary_dry_run'
    assert result['translation']['translated_text'] is None


def test_runtime_translation_boundary_stub_live_missing_bridge():
    set_provider_health('argos_bridge', 'healthy', latency_ms=150, error_rate=0.01, notes='registered boundary')
    set_language_capability(CapabilityUpdateRequest(language_id='lang:spa', capability_name='translation', maturity='experimental', confidence=0.7, provider='argos_bridge', notes='future bridge'))
    set_language_capability(CapabilityUpdateRequest(language_id='lang:eng', capability_name='translation', maturity='experimental', confidence=0.7, provider='argos_bridge', notes='future bridge'))
    result = route_runtime_translation(RuntimeTranslateRequest(text='hola mundo', source_language_id='lang:spa', target_language_id='lang:eng', preferred_translation_provider='argos_bridge', dry_run=False))
    assert result['ok'] is False
    assert result['error'] == 'translation_backend_live_bridge_missing'
    assert result['receipt']['status'] == 'blocked'
