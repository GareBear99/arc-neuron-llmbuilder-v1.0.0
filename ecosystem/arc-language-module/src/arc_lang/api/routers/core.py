from __future__ import annotations

from fastapi import APIRouter

from arc_lang.version import VERSION

from arc_lang.api.http import raise_http_error_if, raise_http_error_unless_ok
from arc_lang.core.db import init_db
from arc_lang.core.models import (
    CapabilityUpdateRequest,
    ImportRequest,
    LanguageSubmissionRequest,
    ManualLineageRequest,
    ReviewDecisionRequest,
    SpeechRequest,
    TranslationExplainRequest,
    TranslateExplainQuery,
    TransliterationRequest,
)
from arc_lang.services.arbitration import resolve_effective_lineage
from arc_lang.services.detection import detect_language
from arc_lang.services.etymology import get_etymology
from arc_lang.services.governance import (
    get_language_readiness,
    list_language_capabilities,
    list_review_decisions,
    record_review_decision,
    set_language_capability,
)
from arc_lang.services.importers import import_cldr_json, import_glottolog_csv, import_iso639_csv
from arc_lang.services.lineage import get_lineage
from arc_lang.services.manual_lineage import add_custom_lineage, list_custom_lineage
from arc_lang.services.onboarding import (
    approve_language_submission,
    export_language_submission_template,
    import_language_submission_json,
    list_language_submissions,
    submit_language,
)
from arc_lang.services.search import search_languages
from arc_lang.services.release_integrity import get_release_snapshot
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.speech_provider import get_provider
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.translation_assertions import create_translation_assertion
from arc_lang.services.translate_explain import translate_explain
from arc_lang.services.transliteration import transliterate, transliterate_request

router = APIRouter()


@router.get('/health')
def health() -> dict:
    return {'ok': True, 'service': 'arc_language_module', 'version': VERSION}


@router.post('/init-db')
def init_database() -> dict:
    init_db()
    return {'ok': True}


@router.get('/release-snapshot')
def release_snapshot() -> dict:
    return get_release_snapshot()


@router.post('/seed/common')
def seed_common() -> dict:
    return ingest_common_seed()


@router.get('/detect')
def detect(text: str) -> dict:
    return detect_language(text).model_dump()


@router.get('/lineage/{language_id}')
def lineage(language_id: str) -> dict:
    return raise_http_error_unless_ok(get_lineage(language_id), status_code=404)


@router.get('/transliterate')
def translit(text: str, source_script: str, target_script: str = 'Latn', language_id: str | None = None) -> dict:
    return transliterate(text=text, source_script=source_script, target_script=target_script, language_id=language_id)


@router.post('/transliterate')
def translit_post(req: TransliterationRequest) -> dict:
    return transliterate_request(req)


@router.post('/translation-assertions')
def translation_assertions(req: TranslationExplainRequest) -> dict:
    return create_translation_assertion(req)


@router.post('/translate-explain')
def translate_explain_route(req: TranslateExplainQuery) -> dict:
    result = translate_explain(req)
    raise_http_error_if(not result.get('ok') and result.get('error') == 'source_language_unknown', status_code=422, detail=result)
    return result


@router.post('/speak/{provider_name}')
def speak(provider_name: str, req: SpeechRequest) -> dict:
    provider = get_provider(provider_name)
    return provider.speak(req)


@router.post('/import/glottolog')
def import_glottolog(req: ImportRequest, dry_run: bool = False) -> dict:
    return import_glottolog_csv(req.path, dry_run=dry_run)


@router.post('/import/iso639_3')
def import_iso(req: ImportRequest, dry_run: bool = False) -> dict:
    return import_iso639_csv(req.path, dry_run=dry_run)


@router.post('/import/cldr')
def import_cldr(req: ImportRequest, dry_run: bool = False) -> dict:
    return import_cldr_json(req.path, dry_run=dry_run)


@router.get('/search/languages')
def search_language_route(q: str, limit: int = 20) -> dict:
    return search_languages(q, limit=limit)


@router.get('/etymology/{language_id}')
def etymology(language_id: str, lemma: str) -> dict:
    return raise_http_error_unless_ok(get_etymology(language_id, lemma), status_code=404)


@router.get('/stats')
def stats() -> dict:
    return get_graph_stats()


@router.post('/lineage/custom')
def add_lineage_custom(req: ManualLineageRequest) -> dict:
    return add_custom_lineage(req)


@router.get('/lineage/custom')
def list_lineage_custom(src_id: str | None = None, dst_id: str | None = None, status: str | None = None) -> dict:
    return list_custom_lineage(src_id=src_id, dst_id=dst_id, status=status)


@router.post('/languages/submit')
def submit_language_route(req: LanguageSubmissionRequest) -> dict:
    return submit_language(req)


@router.get('/languages/submissions')
def list_language_submissions_route(status: str | None = None) -> dict:
    return list_language_submissions(status=status)


@router.post('/languages/submissions/{submission_id}/approve')
def approve_language_submission_route(submission_id: str, status: str = 'approved') -> dict:
    return approve_language_submission(submission_id, status=status)


@router.post('/languages/submissions/import-json')
def import_language_submission_route(req: ImportRequest) -> dict:
    return import_language_submission_json(req.path)


@router.post('/languages/submissions/export-template')
def export_language_submission_template_route(req: ImportRequest) -> dict:
    return export_language_submission_template(req.path)


@router.post('/governance/review')
def review_route(req: ReviewDecisionRequest) -> dict:
    return record_review_decision(req)


@router.get('/governance/reviews')
def review_list_route(target_type: str | None = None, target_id: str | None = None) -> dict:
    return list_review_decisions(target_type=target_type, target_id=target_id)


@router.post('/capabilities/set')
def capability_set_route(req: CapabilityUpdateRequest) -> dict:
    return set_language_capability(req)


@router.get('/capabilities')
def capability_list_route(language_id: str | None = None) -> dict:
    return list_language_capabilities(language_id=language_id)


@router.get('/capabilities/{language_id}/readiness')
def readiness_route(language_id: str) -> dict:
    return raise_http_error_unless_ok(get_language_readiness(language_id), status_code=404)


@router.get('/lineage/{language_id}/effective')
def effective_lineage_route(language_id: str) -> dict:
    return raise_http_error_unless_ok(resolve_effective_lineage(language_id), status_code=404)
