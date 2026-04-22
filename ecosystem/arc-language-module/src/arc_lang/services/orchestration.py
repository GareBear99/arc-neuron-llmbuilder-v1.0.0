from __future__ import annotations

from arc_lang.core.db import connect
from arc_lang.core.models import RuntimeTranslateRequest, RuntimeSpeechRequest, SpeechRequest
from arc_lang.services.detection import detect_language
from arc_lang.services.speech_provider import get_provider
from arc_lang.services.translation_backends import get_translation_backend
from arc_lang.services.provider_registry import provider_is_usable
from arc_lang.services.runtime_receipts import create_job_receipt
from arc_lang.services.policy import get_policy_flag

MATURITY_ORDER = {"none": 0, "seeded": 1, "experimental": 2, "reviewed": 3, "production": 4}


def _best_capability(language_id: str, capability_name: str, provider: str | None = None) -> dict | None:
    """Return the highest-maturity capability record for a language, optionally filtered by provider."""
    query = 'SELECT language_id, capability_name, maturity, confidence, provider, notes FROM language_capabilities WHERE language_id = ? AND capability_name = ?'
    params = [language_id, capability_name]
    if provider:
        query += ' AND provider = ?'
        params.append(provider)
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    if not rows:
        return None
    rows.sort(key=lambda r: (MATURITY_ORDER.get(r['maturity'], -1), r['confidence']), reverse=True)
    return rows[0]


def _is_capability_usable(cap: dict | None, minimum: str = 'seeded') -> bool:
    """Return True if the capability meets the minimum maturity threshold."""
    if not cap:
        return False
    return MATURITY_ORDER.get(cap['maturity'], -1) >= MATURITY_ORDER.get(minimum, 0)


def _translation_provider_summary(source_language_id: str, target_language_id: str, preferred_provider: str | None = None) -> dict:
    """Build a routing summary for a source→target translation request."""
    source_cap = _best_capability(source_language_id, 'translation', preferred_provider) or _best_capability(source_language_id, 'translation')
    target_cap = _best_capability(target_language_id, 'translation', preferred_provider) or _best_capability(target_language_id, 'translation')
    local_seed_ok = bool(_best_capability(source_language_id, 'translation', 'local_seed') or _best_capability(target_language_id, 'translation', 'local_seed'))
    selected_provider = preferred_provider or None
    if not selected_provider:
        if local_seed_ok:
            selected_provider = 'local_seed'
        elif target_cap:
            selected_provider = target_cap['provider']
        elif source_cap:
            selected_provider = source_cap['provider']
        else:
            selected_provider = 'unavailable'
    provider_health = None if selected_provider in {'local_seed', 'unavailable'} else provider_is_usable(selected_provider)
    return {
        'selected_provider': selected_provider,
        'source_capability': source_cap,
        'target_capability': target_cap,
        'local_seed_ok': local_seed_ok,
        'provider_health': provider_health,
    }


def route_runtime_translation(req: RuntimeTranslateRequest) -> dict:
    """Route a runtime translation request through the provider system."""
    detection = None
    source_language_id = req.source_language_id
    if not source_language_id and req.allow_detect:
        detection = detect_language(req.text)
        source_language_id = detection.winner_language_id
    if not source_language_id:
        response = {'ok': False, 'error': 'source_language_unknown', 'detection': detection.model_dump() if detection else None}
        receipt = create_job_receipt('translation', None, req.model_dump(), response, 'failed', ['Source language could not be resolved.'])
        response['receipt'] = receipt
        return response

    provider_summary = _translation_provider_summary(source_language_id, req.target_language_id, req.preferred_translation_provider)
    selected_provider = provider_summary['selected_provider']
    if not req.dry_run and selected_provider in {'argos_bridge', 'nllb_bridge'} and not get_policy_flag('allow_external_providers', False):
        response = {'ok': False, 'error': 'external_provider_blocked_by_policy', 'source_language_id': source_language_id, 'target_language_id': req.target_language_id, 'routing': provider_summary, 'detection': detection.model_dump() if detection else None}
        receipt = create_job_receipt('translation', selected_provider, req.model_dump(), response, 'blocked', ['Policy allow_external_providers=false blocks bridge-style providers.'])
        response['receipt'] = receipt
        return response
    if provider_summary['provider_health'] and not provider_summary['provider_health'].get('usable'):
        response = {
            'ok': False,
            'error': 'translation_provider_unhealthy',
            'source_language_id': source_language_id,
            'target_language_id': req.target_language_id,
            'routing': provider_summary,
            'detection': detection.model_dump() if detection else None,
        }
        receipt = create_job_receipt('translation', selected_provider, req.model_dump(), response, 'blocked', ['Selected translation provider is unhealthy or offline.'])
        response['receipt'] = receipt
        return response

    if not _is_capability_usable(provider_summary['source_capability']) and not _is_capability_usable(provider_summary['target_capability']):
        response = {
            'ok': False,
            'error': 'translation_capability_unavailable',
            'source_language_id': source_language_id,
            'target_language_id': req.target_language_id,
            'detection': detection.model_dump() if detection else None,
            'routing': provider_summary,
        }
        receipt = create_job_receipt('translation', selected_provider if selected_provider != 'unavailable' else None, req.model_dump(), response, 'failed', ['No usable translation capability is registered.'])
        response['receipt'] = receipt
        return response

    backend = get_translation_backend(selected_provider)
    if not backend:
        response = {
            'ok': False,
            'error': 'translation_backend_unregistered',
            'source_language_id': source_language_id,
            'target_language_id': req.target_language_id,
            'routing': provider_summary,
            'notes': ['No built-in backend adapter is available for the selected translation provider.'],
        }
        receipt = create_job_receipt('translation', selected_provider if selected_provider != 'unavailable' else None, req.model_dump(), response, 'failed', response['notes'])
        response['receipt'] = receipt
        return response

    backend_result = backend.translate(req, source_language_id)
    if not backend_result.get('ok'):
        response = {
            'ok': False,
            'error': backend_result.get('error', 'translation_backend_failed'),
            'source_language_id': source_language_id,
            'target_language_id': req.target_language_id,
            'detection': detection.model_dump() if detection else None,
            'routing': provider_summary,
            'backend': backend_result,
            'notes': backend_result.get('notes', []),
        }
        status = 'failed'
        if response['error'] in {'translation_backend_live_bridge_missing'}:
            status = 'blocked'
        receipt = create_job_receipt('translation', selected_provider if selected_provider != 'unavailable' else None, req.model_dump(), response, status, response['notes'])
        response['receipt'] = receipt
        return response

    translation = backend_result['translation']
    routed_by = [backend_result.get('mode', 'backend_unknown')]
    response = {
        'ok': True,
        'mode': 'runtime_translate',
        'source_language_id': source_language_id,
        'target_language_id': req.target_language_id,
        'translation': translation,
        'routing': provider_summary,
        'backend': {
            'provider': backend_result.get('provider', selected_provider),
            'mode': backend_result.get('mode'),
            'notes': backend_result.get('notes', []),
            'dispatch_payload': backend_result.get('dispatch_payload'),
        },
        'routed_by': routed_by,
        'detection': detection.model_dump() if detection else None,
    }

    translated_text = translation.get('translated_text') if isinstance(translation, dict) else None
    if (req.require_speech or req.speech_provider) and translated_text:
        speech = route_runtime_speech(RuntimeSpeechRequest(
            text=translated_text,
            language_id=req.target_language_id,
            provider=req.speech_provider,
            voice_hint=req.voice_hint,
            dry_run=req.dry_run,
        ))
        response['speech'] = speech
        if req.require_speech and not speech.get('ok'):
            response['ok'] = False
            response['error'] = 'speech_capability_unavailable'
            receipt = create_job_receipt('translation', selected_provider if selected_provider != 'unavailable' else None, req.model_dump(), response, 'partial_failure', ['Translation succeeded but speech routing failed.'])
            response['receipt'] = receipt
            return response

    receipt = create_job_receipt('translation', selected_provider if selected_provider != 'unavailable' else None, req.model_dump(), response, 'succeeded', ['Runtime translation completed.'])
    response['receipt'] = receipt
    return response



def route_runtime_speech(req: RuntimeSpeechRequest) -> dict:
    """Route a runtime speech synthesis request through the provider system."""
    if not req.dry_run and get_policy_flag("runtime_default_dry_run", True):
        response = {"ok": False, "error": "runtime_live_execution_blocked_by_policy", "language_id": req.language_id, "requested_provider": req.provider}
        receipt = create_job_receipt("speech", req.provider, req.model_dump(), response, "blocked", ["Policy runtime_default_dry_run=true blocks live speech execution."])
        response["receipt"] = receipt
        return response
    if not req.dry_run and not get_policy_flag("allow_live_speech", False):
        response = {"ok": False, "error": "live_speech_blocked_by_policy", "language_id": req.language_id, "requested_provider": req.provider}
        receipt = create_job_receipt("speech", req.provider, req.model_dump(), response, "blocked", ["Policy allow_live_speech=false blocks live speech execution."])
        response["receipt"] = receipt
        return response
    cap = _best_capability(req.language_id, 'speech', req.provider) or _best_capability(req.language_id, 'speech')
    if not _is_capability_usable(cap, minimum='experimental'):
        response = {
            'ok': False,
            'error': 'speech_capability_unavailable',
            'language_id': req.language_id,
            'requested_provider': req.provider,
            'capability': cap,
        }
        receipt = create_job_receipt('speech', req.provider, req.model_dump(), response, 'failed', ['Speech capability is below minimum runtime threshold.'])
        response['receipt'] = receipt
        return response
    provider_name = req.provider or cap['provider']
    health = provider_is_usable(provider_name)
    if not health.get('usable'):
        response = {
            'ok': False,
            'error': 'speech_provider_unhealthy',
            'language_id': req.language_id,
            'requested_provider': provider_name,
            'capability': cap,
            'provider_health': health,
        }
        receipt = create_job_receipt('speech', provider_name, req.model_dump(), response, 'blocked', ['Speech provider is unhealthy or disabled.'])
        response['receipt'] = receipt
        return response
    provider = get_provider(provider_name)
    result = provider.speak(SpeechRequest(text=req.text, language_id=req.language_id, voice_hint=req.voice_hint, dry_run=req.dry_run))
    result['capability'] = cap
    result['provider_health'] = health
    receipt = create_job_receipt('speech', provider_name, req.model_dump(), result, 'succeeded' if result.get('ok') else 'failed', ['Runtime speech dispatch executed.'])
    result['receipt'] = receipt
    return result
