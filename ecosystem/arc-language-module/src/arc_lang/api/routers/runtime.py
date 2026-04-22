from __future__ import annotations

from fastapi import APIRouter

from arc_lang.api.http import raise_http_error_if, raise_http_error_unless_ok
from arc_lang.core.models import (
    AnalysisRequest,
    BackendActionRequest,
    EvidenceExportRequest,
    PolicyUpdateRequest,
    PronunciationRequest,
    ProviderHealthRequest,
    ProviderRegistrationRequest,
    RuntimeSpeechRequest,
    RuntimeTranslateRequest,
    TranslationInstallPlanRequest,
    TransliterationProfileUpsertRequest,
)
from arc_lang.services.backend_diagnostics import (
    get_provider_diagnostics,
    get_translation_pair_readiness,
    get_translation_readiness_matrix,
)
from arc_lang.services.evidence_export import export_evidence_bundle
from arc_lang.services.linguistic_analysis import analyze_text
from arc_lang.services.orchestration import route_runtime_speech, route_runtime_translation
from arc_lang.services.package_lifecycle import (
    build_translation_install_plan,
    list_translation_install_plans,
    record_translation_install_plan,
)
from arc_lang.services.policy import get_policy_snapshot, set_operator_policy
from arc_lang.services.provider_actions import (
    build_provider_action_catalog,
    execute_provider_action,
    list_provider_action_receipts,
)
from arc_lang.services.provider_registry import list_providers, register_provider, set_provider_health
from arc_lang.services.pronunciation import list_pronunciation_profiles, pronunciation_guide
from arc_lang.services.runtime_receipts import list_job_receipts
from arc_lang.services.system_status import get_system_status
from arc_lang.services.translation_backends import list_builtin_translation_backends
from arc_lang.services.transliteration import list_transliteration_profiles, upsert_transliteration_profile

router = APIRouter()


@router.post('/runtime/translate')
def runtime_translate_route(req: RuntimeTranslateRequest) -> dict:
    result = route_runtime_translation(req)
    raise_http_error_if(
        not result.get('ok') and result.get('error') in {'source_language_unknown', 'translation_capability_unavailable', 'speech_capability_unavailable'},
        status_code=422,
        detail=result,
    )
    return result


@router.post('/runtime/speak')
def runtime_speak_route(req: RuntimeSpeechRequest) -> dict:
    result = route_runtime_speech(req)
    raise_http_error_if(not result.get('ok'), status_code=422, detail=result)
    return result


@router.post('/providers/register')
def provider_register_route(req: ProviderRegistrationRequest) -> dict:
    return register_provider(req.provider_name, req.provider_type, enabled=req.enabled, local_only=req.local_only, notes=req.notes)


@router.post('/providers/health')
def provider_health_route(req: ProviderHealthRequest) -> dict:
    return set_provider_health(req.provider_name, req.status, latency_ms=req.latency_ms, error_rate=req.error_rate, notes=req.notes)


@router.get('/providers')
def providers_route(provider_type: str | None = None) -> dict:
    return list_providers(provider_type=provider_type)


@router.get('/runtime/receipts')
def runtime_receipts_route(job_type: str | None = None, provider_name: str | None = None, limit: int = 50) -> dict:
    return list_job_receipts(job_type=job_type, provider_name=provider_name, limit=limit)


@router.get('/providers/translation-backends')
def translation_backends_route() -> dict:
    return list_builtin_translation_backends()


@router.get('/providers/diagnostics')
def provider_diagnostics_route(provider_name: str | None = None) -> dict:
    return get_provider_diagnostics(provider_name=provider_name)


@router.get('/runtime/readiness/translation')
def translation_readiness_route(source_language_id: str, target_language_id: str, provider_name: str | None = None) -> dict:
    return raise_http_error_unless_ok(
        get_translation_pair_readiness(source_language_id, target_language_id, provider_name=provider_name),
        status_code=404,
    )


@router.get('/runtime/readiness/matrix')
def translation_readiness_matrix_route(target_language_id: str | None = None, provider_name: str | None = None, limit: int = 25) -> dict:
    return get_translation_readiness_matrix(target_language_id=target_language_id, provider_name=provider_name, limit=limit)


@router.get('/runtime/install-plan/translation')
def translation_install_plan_route(source_language_id: str, target_language_id: str, provider_name: str = 'argos_local') -> dict:
    return raise_http_error_unless_ok(
        build_translation_install_plan(source_language_id, target_language_id, provider_name=provider_name),
        status_code=404,
    )


@router.post('/runtime/install-plan/translation/record')
def translation_install_plan_record_route(req: TranslationInstallPlanRequest) -> dict:
    return raise_http_error_unless_ok(
        record_translation_install_plan(req.source_language_id, req.target_language_id, provider_name=req.provider_name, notes=req.notes),
        status_code=404,
    )


@router.get('/runtime/install-plans')
def translation_install_plans_route(provider_name: str | None = None, source_language_id: str | None = None, target_language_id: str | None = None, limit: int = 50) -> dict:
    return list_translation_install_plans(provider_name=provider_name, source_language_id=source_language_id, target_language_id=target_language_id, limit=limit)


@router.get('/runtime/provider-actions')
def provider_actions_route(source_language_id: str, target_language_id: str, provider_name: str) -> dict:
    return build_provider_action_catalog(source_language_id, target_language_id, provider_name)


@router.post('/runtime/provider-actions/execute')
def provider_actions_execute_route(req: BackendActionRequest) -> dict:
    result = execute_provider_action(req)
    raise_http_error_if(
        not result.get('ok') and result.get('error') in {'provider_action_unknown', 'provider_action_mutation_blocked'},
        status_code=422,
        detail=result,
    )
    return result


@router.get('/runtime/provider-action-receipts')
def provider_action_receipts_route(provider_name: str | None = None, action_name: str | None = None, limit: int = 50) -> dict:
    return list_provider_action_receipts(provider_name=provider_name, action_name=action_name, limit=limit)


@router.get('/system/status')
def system_status_route() -> dict:
    return get_system_status()


@router.get('/policy')
def policy_route() -> dict:
    return get_policy_snapshot()


@router.post('/policy/set')
def policy_set_route(req: PolicyUpdateRequest) -> dict:
    return set_operator_policy(req.policy_key, req.policy_value, notes=req.notes)


@router.post('/evidence/export')
def evidence_export_route(req: EvidenceExportRequest) -> dict:
    return export_evidence_bundle(req.output_path, language_ids=req.language_ids, include_receipts=req.include_receipts, include_runtime=req.include_runtime, include_graph=req.include_graph)


@router.get('/transliteration/profiles')
def transliteration_profiles_route(language_id: str | None = None) -> dict:
    return list_transliteration_profiles(language_id=language_id)


@router.post('/transliteration/profiles/upsert')
def transliteration_profile_upsert_route(req: TransliterationProfileUpsertRequest) -> dict:
    return upsert_transliteration_profile(req.language_id, req.source_script, req.target_script, req.scheme_name, req.coverage, example_in=req.example_in, example_out=req.example_out, notes=req.notes)


@router.post('/pronounce')
def pronounce_route(req: PronunciationRequest) -> dict:
    result = pronunciation_guide(req)
    raise_http_error_if(not result.get('ok'), status_code=422, detail=result)
    return result


@router.get('/pronunciation/profiles')
def pronunciation_profiles_route(language_id: str | None = None) -> dict:
    return list_pronunciation_profiles(language_id=language_id)


@router.post('/analyze')
def analyze_route(req: AnalysisRequest) -> dict:
    result = analyze_text(req)
    raise_http_error_if(not result.get('ok'), status_code=422, detail=result)
    return result
