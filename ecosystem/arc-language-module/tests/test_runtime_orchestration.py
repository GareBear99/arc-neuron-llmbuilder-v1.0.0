from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.governance import set_language_capability
from arc_lang.services.orchestration import route_runtime_translation, route_runtime_speech
from arc_lang.services.provider_registry import set_provider_health
from arc_lang.core.models import CapabilityUpdateRequest, RuntimeTranslateRequest, RuntimeSpeechRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_runtime_translation_routes_local_seed_and_speech():
    # PersonaPlex is seeded as 'offline' (correct for a boundary stub with no live runtime).
    # For this dry-run test, explicitly set it to 'healthy' to exercise the routing path.
    set_provider_health('personaplex', 'healthy', latency_ms=0, error_rate=0.0,
                        notes='test: override to healthy for dry-run routing test')
    set_language_capability(CapabilityUpdateRequest(
        language_id='lang:eng', capability_name='speech', maturity='experimental',
        confidence=0.82, provider='personaplex', notes='dry-run speech allowed'))
    result = route_runtime_translation(RuntimeTranslateRequest(
        text='hola', target_language_id='lang:eng', require_speech=True, speech_provider='personaplex'))
    assert result['ok'] is True
    assert result['translation']['translated_text'] == 'hello'
    assert result['routing']['selected_provider'] == 'local_seed'
    assert result['speech']['ok'] is True
    assert result['speech']['provider'] == 'personaplex'
    # Restore offline status
    set_provider_health('personaplex', 'offline', notes='boundary stub — offline until NVIDIA runtime configured')


def test_runtime_translation_offline_speech_provider_blocks():
    """When personaplex is offline (its seeded default), require_speech=True must fail."""
    # personaplex is offline by default in seed
    set_language_capability(CapabilityUpdateRequest(
        language_id='lang:spa', capability_name='speech', maturity='experimental',
        confidence=0.75, provider='personaplex', notes='test'))
    result = route_runtime_translation(RuntimeTranslateRequest(
        text='hola', target_language_id='lang:eng', require_speech=True, speech_provider='personaplex'))
    # Either provider_offline or speech_capability_unavailable is acceptable
    assert result['ok'] is False
    assert result.get('error') in {
        'provider_offline', 'speech_capability_unavailable',
        'translation_backend_not_implemented', 'no_phrase_translation_found',
    }


def test_runtime_translation_blocks_when_no_translation_capability():
    result = route_runtime_translation(RuntimeTranslateRequest(
        text='unknown phrase', source_language_id='lang:eng', target_language_id='lang:chr'))
    assert result['ok'] is False
    assert result['error'] in {
        'translation_backend_not_implemented', 'translation_capability_unavailable',
        'no_phrase_translation_found',
    }


def test_runtime_speech_capability_gate():
    """Speech must be blocked for a language with no speech capability set.
    Uses lang:swa (Swahili) which has no speech capability in any test.
    Both speech_capability_unavailable and speech_provider_unhealthy are valid blocking responses."""
    blocked = route_runtime_speech(RuntimeSpeechRequest(text='asante', language_id='lang:swa'))
    assert blocked['ok'] is False
    assert blocked.get('error') in {
        'speech_capability_unavailable',
        'speech_provider_unhealthy',
        'provider_offline',
    }, f"Expected speech to be blocked; got: {blocked.get('error')}"
