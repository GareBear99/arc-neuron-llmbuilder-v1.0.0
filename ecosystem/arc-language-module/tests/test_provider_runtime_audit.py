from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.governance import set_language_capability
from arc_lang.services.provider_registry import list_providers, set_provider_health
from arc_lang.services.runtime_receipts import list_job_receipts
from arc_lang.services.orchestration import route_runtime_translation, route_runtime_speech
from arc_lang.core.models import CapabilityUpdateRequest, RuntimeTranslateRequest, RuntimeSpeechRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_provider_registry_seeded_and_receipts_created():
    providers = list_providers()
    names = {p['provider_name'] for p in providers['providers']}
    assert 'personaplex' in names
    assert 'local_seed' in names

    result = route_runtime_translation(RuntimeTranslateRequest(text='hola', target_language_id='lang:eng'))
    assert result['ok'] is True
    assert result['receipt']['status'] == 'succeeded'

    receipts = list_job_receipts(job_type='translation')
    assert any(r['receipt_id'] == result['receipt']['receipt_id'] for r in receipts['receipts'])


def test_offline_speech_provider_blocks_runtime_speech():
    set_language_capability(CapabilityUpdateRequest(language_id='lang:eng', capability_name='speech', maturity='experimental', confidence=0.82, provider='personaplex', notes='dry-run speech allowed'))
    set_provider_health('personaplex', 'offline', latency_ms=9999, error_rate=1.0, notes='simulated outage')
    blocked = route_runtime_speech(RuntimeSpeechRequest(text='hello', language_id='lang:eng', provider='personaplex'))
    assert blocked['ok'] is False
    assert blocked['error'] == 'speech_provider_unhealthy'
    assert blocked['receipt']['status'] == 'blocked'
