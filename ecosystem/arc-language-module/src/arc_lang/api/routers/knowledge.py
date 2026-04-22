from __future__ import annotations

from fastapi import APIRouter

from arc_lang.api.http import raise_http_error_unless_ok
from arc_lang.core.models import (
    AliasUpsertRequest,
    BatchExportRequest,
    BatchImportRequest,
    ConceptLinkRequest,
    ConflictReviewExportRequest,
    CoverageReportRequest,
    LanguageVariantUpsertRequest,
    PhonologyProfileUpsertRequest,
    RelationshipAssertionRequest,
    SemanticConceptUpsertRequest,
    SourceWeightUpdateRequest,
)
from arc_lang.services.aliases import list_language_aliases, upsert_language_alias
from arc_lang.services.batch_io import batch_export, batch_import, list_batch_runs
from arc_lang.services.concepts import get_concept_bundle, link_concept, list_semantic_concepts, upsert_semantic_concept
from arc_lang.services.conflict_review import export_conflict_review_bundle, list_conflict_review_exports
from arc_lang.services.coverage import build_coverage_report, list_coverage_reports
from arc_lang.services.implementation_matrix import build_implementation_matrix, list_implementation_matrix_reports
from arc_lang.services.manifests import list_backend_manifests, list_corpus_manifests
from arc_lang.services.phonology import list_phonology_profiles, phonology_hint, upsert_phonology_profile
from arc_lang.services.relationships import add_relationship_assertion, list_relationship_assertions
from arc_lang.services.source_policy import list_source_weights, set_source_weight
from arc_lang.services.variants import list_language_variants, upsert_language_variant

router = APIRouter()


@router.post('/languages/aliases/upsert')
def alias_upsert_route(req: AliasUpsertRequest) -> dict:
    return upsert_language_alias(req)


@router.get('/languages/aliases')
def alias_list_route(language_id: str | None = None, q: str | None = None) -> dict:
    return list_language_aliases(language_id=language_id, q=q)


@router.post('/relationships/assert')
def relationship_assert_route(req: RelationshipAssertionRequest) -> dict:
    return add_relationship_assertion(req)


@router.get('/relationships')
def relationship_list_route(lexeme_id: str | None = None, relation: str | None = None) -> dict:
    return list_relationship_assertions(lexeme_id=lexeme_id, relation=relation)


@router.post('/batch/import')
def batch_import_route(req: BatchImportRequest) -> dict:
    return batch_import(req)


@router.post('/batch/export')
def batch_export_route(req: BatchExportRequest) -> dict:
    return batch_export(req)


@router.get('/batch/runs')
def batch_runs_route(mode: str | None = None, object_type: str | None = None) -> dict:
    return list_batch_runs(mode=mode, object_type=object_type)


@router.post('/sources/weights/set')
def source_weight_set_route(req: SourceWeightUpdateRequest) -> dict:
    return set_source_weight(req)


@router.get('/sources/weights')
def source_weight_list_route() -> dict:
    return list_source_weights()


@router.post('/concepts/upsert')
def concepts_upsert_route(req: SemanticConceptUpsertRequest) -> dict:
    return upsert_semantic_concept(req)


@router.post('/concepts/link')
def concepts_link_route(req: ConceptLinkRequest) -> dict:
    return link_concept(req)


@router.get('/concepts')
def concepts_list_route(domain: str | None = None, q: str | None = None) -> dict:
    return list_semantic_concepts(domain=domain, q=q)


@router.get('/concepts/{concept_id}')
def concepts_bundle_route(concept_id: str) -> dict:
    return raise_http_error_unless_ok(get_concept_bundle(concept_id), status_code=404)


@router.post('/languages/variants/upsert')
def variants_upsert_route(req: LanguageVariantUpsertRequest) -> dict:
    return upsert_language_variant(req)


@router.get('/languages/variants')
def variants_list_route(language_id: str | None = None, variant_type: str | None = None) -> dict:
    return list_language_variants(language_id=language_id, variant_type=variant_type)


@router.post('/conflicts/export')
def conflicts_export_route(req: ConflictReviewExportRequest) -> dict:
    return export_conflict_review_bundle(req)


@router.get('/conflicts/exports')
def conflicts_exports_list_route(limit: int = 20) -> dict:
    return list_conflict_review_exports(limit=limit)


@router.post('/coverage/report')
def coverage_report_route(req: CoverageReportRequest) -> dict:
    return build_coverage_report(req)


@router.get('/coverage/reports')
def coverage_reports_route(limit: int = 20) -> dict:
    return list_coverage_reports(limit=limit)


@router.get('/phonology/profiles')
def phonology_profiles_route(language_id: str | None = None) -> dict:
    return list_phonology_profiles(language_id=language_id)


@router.post('/phonology/profiles/upsert')
def phonology_upsert_route(req: PhonologyProfileUpsertRequest) -> dict:
    return upsert_phonology_profile(
        req.language_id,
        req.notation_system,
        broad_ipa=req.broad_ipa,
        stress_policy=req.stress_policy,
        syllable_template=req.syllable_template,
        examples=req.examples or None,
        notes=req.notes,
    )


@router.get('/phonology/hint')
def phonology_hint_route(text: str, language_id: str) -> dict:
    return raise_http_error_unless_ok(phonology_hint(text, language_id), status_code=404)


@router.get('/backend-manifests')
def backend_manifests_route(provider_name: str | None = None) -> dict:
    return list_backend_manifests(provider_name=provider_name)


@router.get('/corpus-manifests')
def corpus_manifests_route(corpus_kind: str | None = None) -> dict:
    return list_corpus_manifests(corpus_kind=corpus_kind)


@router.post('/implementation-matrix')
def implementation_matrix_route(output_path: str | None = None) -> dict:
    return build_implementation_matrix(output_path=output_path)


@router.get('/implementation-matrix/reports')
def implementation_matrix_reports_route(limit: int = 20) -> dict:
    return list_implementation_matrix_reports(limit=limit)
