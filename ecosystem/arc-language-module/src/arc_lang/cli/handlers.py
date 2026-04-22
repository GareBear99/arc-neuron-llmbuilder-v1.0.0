from __future__ import annotations
import argparse
import json
from arc_lang.core.db import init_db
from arc_lang.core.models import TranslateExplainQuery, ManualLineageRequest, LanguageSubmissionRequest, ReviewDecisionRequest, CapabilityUpdateRequest, RuntimeTranslateRequest, RuntimeSpeechRequest, BackendActionRequest, PronunciationRequest, AnalysisRequest, TransliterationRequest, AliasUpsertRequest, RelationshipAssertionRequest, BatchImportRequest, BatchExportRequest, SourceWeightUpdateRequest, SemanticConceptUpsertRequest, ConceptLinkRequest, LanguageVariantUpsertRequest, ConflictReviewExportRequest, CoverageReportRequest, AcquisitionJobRequest, StagedAssetRequest, ValidationReportRequest, IngestionWorkspaceExportRequest
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.detection import detect_language, detect_script
from arc_lang.services.lineage import get_lineage
from arc_lang.services.transliteration import transliterate, transliterate_request, list_transliteration_profiles, upsert_transliteration_profile
from arc_lang.services.translate_explain import translate_explain
from arc_lang.services.importers import import_glottolog_csv, import_iso639_csv, import_cldr_json
from arc_lang.services.search import search_languages
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.release_integrity import get_release_snapshot
from arc_lang.services.etymology import get_etymology
from arc_lang.services.manual_lineage import add_custom_lineage, list_custom_lineage
from arc_lang.services.onboarding import submit_language, list_language_submissions, approve_language_submission, export_language_submission_template, import_language_submission_json
from arc_lang.services.governance import record_review_decision, list_review_decisions, set_language_capability, list_language_capabilities, get_language_readiness
from arc_lang.services.arbitration import resolve_effective_lineage
from arc_lang.services.orchestration import route_runtime_translation, route_runtime_speech
from arc_lang.services.provider_registry import register_provider, set_provider_health, list_providers
from arc_lang.services.runtime_receipts import list_job_receipts
from arc_lang.services.translation_backends import list_builtin_translation_backends
from arc_lang.services.backend_diagnostics import get_provider_diagnostics, get_translation_pair_readiness, get_translation_readiness_matrix
from arc_lang.services.package_lifecycle import build_translation_install_plan, record_translation_install_plan, list_translation_install_plans
from arc_lang.services.provider_actions import build_provider_action_catalog, execute_provider_action, list_provider_action_receipts
from arc_lang.services.policy import get_policy_snapshot, set_operator_policy
from arc_lang.services.system_status import get_system_status
from arc_lang.services.evidence_export import export_evidence_bundle
from arc_lang.services.pronunciation import pronunciation_guide, list_pronunciation_profiles
from arc_lang.services.linguistic_analysis import analyze_text
from arc_lang.services.aliases import upsert_language_alias, list_language_aliases
from arc_lang.services.relationships import add_relationship_assertion, list_relationship_assertions
from arc_lang.services.batch_io import batch_import, batch_export, list_batch_runs
from arc_lang.services.source_policy import set_source_weight, list_source_weights
from arc_lang.services.concepts import upsert_semantic_concept, link_concept, list_semantic_concepts, get_concept_bundle
from arc_lang.services.variants import upsert_language_variant, list_language_variants
from arc_lang.services.conflict_review import export_conflict_review_bundle, list_conflict_review_exports
from arc_lang.services.coverage import build_coverage_report, list_coverage_reports
from arc_lang.services.acquisition_workspace import plan_acquisition_job, record_staged_asset, validate_staged_asset, list_acquisition_jobs, list_validation_reports, export_ingestion_workspace
from arc_lang.services.phonology import upsert_phonology_profile, list_phonology_profiles, phonology_hint
from arc_lang.services.implementation_matrix import build_implementation_matrix, list_implementation_matrix_reports
from arc_lang.services.self_fill import scan_self_fill_gaps, list_self_fill_candidates, list_self_fill_scan_runs, promote_self_fill_candidate, reject_self_fill_candidate
from arc_lang.services.self_fill_sources import stage_iso_fixture_candidates, stage_glottolog_fixture_candidates, stage_cldr_fixture_candidates, list_self_fill_import_runs, list_self_fill_conflicts, resolve_self_fill_conflict, run_approved_source_import_bootstrap
from arc_lang.services.self_fill_arbitration import arbitrate_self_fill_candidates, list_self_fill_arbitration_runs, list_self_fill_arbitration_decisions, promote_arbitrated_self_fill_winners, recommend_source_weight
from arc_lang.services.self_fill_release import run_recurring_self_fill_release, list_self_fill_release_runs, list_self_fill_release_artifacts
from arc_lang.services.self_fill_retention import run_scheduled_self_fill_release_cycle, list_self_fill_retention_policies, list_self_fill_retention_actions, list_self_fill_rollback_index
from arc_lang.services.self_fill_replay import build_self_fill_replay_manifest, restore_self_fill_snapshot, compact_self_fill_release, list_self_fill_replay_runs, list_self_fill_compaction_actions


def _dump(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def dispatch(args: argparse.Namespace) -> None:
    if args.cmd == 'init-db': init_db(); _dump({'ok': True}); return
    if args.cmd == 'seed-common-languages': _dump(ingest_common_seed()); return
    if args.cmd == 'stats': _dump(get_graph_stats()); return
    if args.cmd == 'release-snapshot': _dump(get_release_snapshot()); return
    if args.cmd == 'detect': _dump(detect_language(args.text).model_dump()); return
    if args.cmd == 'detect-script': _dump({'ok': True, 'script': detect_script(args.text)}); return
    if args.cmd == 'lineage': _dump(get_lineage(args.language_id)); return
    if args.cmd == 'effective-lineage': _dump(resolve_effective_lineage(args.language_id)); return
    if args.cmd == 'etymology': _dump(get_etymology(args.language_id, args.lemma)); return
    if args.cmd == 'search-languages': _dump(search_languages(args.query, limit=args.limit)); return
    if args.cmd == 'transliterate': _dump(transliterate(args.text, args.source_script, args.target_script)); return
    if args.cmd == 'translate-explain': _dump(translate_explain(TranslateExplainQuery(text=args.text, target_language_id=args.target_language_id, source_language_id=args.source_language_id))); return
    if args.cmd == 'pronounce': _dump(pronunciation_guide(PronunciationRequest(text=args.text, language_id=args.language_id, target_script=args.target_script))); return
    if args.cmd == 'analyze-text': _dump(analyze_text(AnalysisRequest(text=args.text, language_id=args.language_id, include_pronunciation=not args.no_pronunciation))); return
    if args.cmd == 'list-pronunciation-profiles': _dump(list_pronunciation_profiles(language_id=args.language_id)); return
    if args.cmd == 'list-transliteration-profiles': _dump(list_transliteration_profiles(language_id=args.language_id)); return
    if args.cmd == 'upsert-transliteration-profile': _dump(upsert_transliteration_profile(args.language_id, args.source_script, args.target_script, args.scheme_name, args.coverage, example_in=args.example_in, example_out=args.example_out, notes=args.notes)); return
    if args.cmd == 'import-glottolog-fixture': _dump(import_glottolog_csv(args.path, dry_run=args.dry_run)); return
    if args.cmd == 'import-iso-fixture': _dump(import_iso639_csv(args.path, dry_run=args.dry_run)); return
    if args.cmd == 'import-cldr-fixture': _dump(import_cldr_json(args.path, dry_run=args.dry_run)); return
    if args.cmd == 'add-custom-lineage':
        _dump(add_custom_lineage(ManualLineageRequest(src_id=args.src_id, dst_id=args.dst_id, relation=args.relation, confidence=args.confidence, disputed=args.disputed, source_name=args.source_name, source_ref=args.source_ref, notes=args.notes, status=args.status)));
        return
    if args.cmd == 'list-custom-lineage': _dump(list_custom_lineage(src_id=args.src_id, dst_id=args.dst_id, status=args.status)); return
    if args.cmd == 'submit-language-json': _dump(import_language_submission_json(args.path)); return
    if args.cmd == 'submit-language-inline':
        _dump(submit_language(LanguageSubmissionRequest(language_id=args.language_id, name=args.name, iso639_3=args.iso639_3, family=args.family, branch=args.branch, parent_language_id=args.parent_language_id, aliases=args.aliases, common_words=args.common_words, scripts=args.scripts, source_name=args.source_name, source_ref=args.source_ref, confidence=args.confidence, notes=args.notes, status=args.status)));
        return
    if args.cmd == 'list-language-submissions': _dump(list_language_submissions(status=args.status)); return
    if args.cmd == 'approve-language-submission': _dump(approve_language_submission(args.submission_id, status=args.status)); return
    if args.cmd == 'export-language-template': _dump(export_language_submission_template(args.path)); return
    if args.cmd == 'review-target':
        _dump(record_review_decision(ReviewDecisionRequest(target_type=args.target_type, target_id=args.target_id, decision=args.decision, reviewer=args.reviewer, confidence=args.confidence, notes=args.notes)));
        return
    if args.cmd == 'list-reviews': _dump(list_review_decisions(target_type=args.target_type, target_id=args.target_id)); return
    if args.cmd == 'set-language-capability':
        _dump(set_language_capability(CapabilityUpdateRequest(language_id=args.language_id, capability_name=args.capability_name, maturity=args.maturity, confidence=args.confidence, provider=args.provider, notes=args.notes)));
        return
    if args.cmd == 'list-language-capabilities': _dump(list_language_capabilities(language_id=args.language_id)); return
    if args.cmd == 'language-readiness': _dump(get_language_readiness(args.language_id)); return
    if args.cmd == 'runtime-translate':
        _dump(route_runtime_translation(RuntimeTranslateRequest(text=args.text, target_language_id=args.target_language_id, source_language_id=args.source_language_id, preferred_translation_provider=args.preferred_translation_provider, require_speech=args.require_speech, speech_provider=args.speech_provider, voice_hint=args.voice_hint, dry_run=not args.live))); return
    if args.cmd == 'runtime-speak':
        _dump(route_runtime_speech(RuntimeSpeechRequest(text=args.text, language_id=args.language_id, provider=args.provider, voice_hint=args.voice_hint, dry_run=not args.live))); return
    if args.cmd == 'register-provider': _dump(register_provider(args.provider_name, args.provider_type, enabled=not args.disabled, local_only=args.local_only, notes=args.notes)); return
    if args.cmd == 'set-provider-health': _dump(set_provider_health(args.provider_name, args.status, latency_ms=args.latency_ms, error_rate=args.error_rate, notes=args.notes)); return
    if args.cmd == 'list-providers': _dump(list_providers(provider_type=args.provider_type)); return
    if args.cmd == 'list-runtime-receipts': _dump(list_job_receipts(job_type=args.job_type, provider_name=args.provider_name, limit=args.limit)); return
    if args.cmd == 'provider-diagnostics': _dump(get_provider_diagnostics(args.provider_name)); return
    if args.cmd == 'translation-readiness': _dump(get_translation_pair_readiness(args.source_language_id, args.target_language_id, provider_name=args.provider)); return
    if args.cmd == 'translation-readiness-matrix': _dump(get_translation_readiness_matrix(target_language_id=args.target_language_id, provider_name=args.provider, limit=args.limit)); return
    if args.cmd == 'list-translation-backends': _dump(list_builtin_translation_backends()); return
    if args.cmd == 'translation-install-plan': _dump(build_translation_install_plan(args.source_language_id, args.target_language_id, provider_name=args.provider)); return
    if args.cmd == 'record-translation-install-plan': _dump(record_translation_install_plan(args.source_language_id, args.target_language_id, provider_name=args.provider, notes=args.note)); return
    if args.cmd == 'list-translation-install-plans': _dump(list_translation_install_plans(provider_name=args.provider, source_language_id=args.source_language_id, target_language_id=args.target_language_id, limit=args.limit)); return

    if args.cmd == 'system-status': _dump(get_system_status()); return
    if args.cmd == 'show-policy': _dump(get_policy_snapshot()); return
    if args.cmd == 'set-policy': _dump(set_operator_policy(args.policy_key, args.policy_value, notes=args.notes)); return
    if args.cmd == 'export-evidence': _dump(export_evidence_bundle(args.output_path, language_ids=args.language_id, include_receipts=not args.no_receipts, include_runtime=not args.no_runtime, include_graph=not args.no_graph)); return
    if args.cmd == 'provider-action-catalog': _dump(build_provider_action_catalog(args.source_language_id, args.target_language_id, args.provider)); return
    if args.cmd == 'execute-provider-action': _dump(execute_provider_action(BackendActionRequest(provider_name=args.provider, source_language_id=args.source_language_id, target_language_id=args.target_language_id, action_name=args.action_name, dry_run=not args.apply, allow_mutation=args.allow_mutation, notes=args.note))); return
    if args.cmd == 'list-provider-action-receipts': _dump(list_provider_action_receipts(provider_name=args.provider, action_name=args.action_name, limit=args.limit)); return

    if args.cmd == 'upsert-language-alias': _dump(upsert_language_alias(AliasUpsertRequest(language_id=args.language_id, alias=args.alias, alias_type=args.alias_type, normalized_form=args.normalized_form, script_id=args.script_id, region_hint=args.region_hint, source_name=args.source_name, source_ref=args.source_ref, confidence=args.confidence, notes=args.notes))); return
    if args.cmd == 'list-language-aliases': _dump(list_language_aliases(language_id=args.language_id, q=args.query)); return
    if args.cmd == 'assert-relationship': _dump(add_relationship_assertion(RelationshipAssertionRequest(src_lexeme_id=args.src_lexeme_id, dst_lexeme_id=args.dst_lexeme_id, relation=args.relation, confidence=args.confidence, disputed=args.disputed, source_name=args.source_name, source_ref=args.source_ref, notes=args.notes))); return
    if args.cmd == 'list-relationships': _dump(list_relationship_assertions(lexeme_id=args.lexeme_id, relation=args.relation)); return
    if args.cmd == 'batch-import': _dump(batch_import(BatchImportRequest(input_path=args.input_path, object_type=args.object_type, dry_run=not args.apply))); return
    if args.cmd == 'batch-export': _dump(batch_export(BatchExportRequest(output_path=args.output_path, object_type=args.object_type, language_ids=args.language_id, include_provenance=not args.no_provenance))); return
    if args.cmd == 'list-batch-runs': _dump(list_batch_runs(mode=args.mode, object_type=args.object_type)); return
    if args.cmd == 'set-source-weight': _dump(set_source_weight(SourceWeightUpdateRequest(source_name=args.source_name, authority_weight=args.authority_weight, notes=args.notes))); return
    if args.cmd == 'list-source-weights': _dump(list_source_weights()); return
    if args.cmd == 'upsert-semantic-concept': _dump(upsert_semantic_concept(SemanticConceptUpsertRequest(concept_id=args.concept_id, canonical_label=args.canonical_label, domain=args.domain, description=args.description, source_name=args.source_name, source_ref=args.source_ref, confidence=args.confidence))); return
    if args.cmd == 'link-concept': _dump(link_concept(ConceptLinkRequest(concept_id=args.concept_id, target_type=args.target_type, target_id=args.target_id, relation=args.relation, confidence=args.confidence, notes=args.notes))); return
    if args.cmd == 'list-concepts': _dump(list_semantic_concepts(domain=args.domain, q=args.query)); return
    if args.cmd == 'concept-bundle': _dump(get_concept_bundle(args.concept_id)); return
    if args.cmd == 'upsert-language-variant': _dump(upsert_language_variant(LanguageVariantUpsertRequest(language_id=args.language_id, variant_name=args.variant_name, variant_type=args.variant_type, region_hint=args.region_hint, script_id=args.script_id, status=args.status, mutual_intelligibility=args.mutual_intelligibility, notes=args.notes))); return
    if args.cmd == 'list-language-variants': _dump(list_language_variants(language_id=args.language_id, variant_type=args.variant_type)); return
    if args.cmd == 'export-conflict-review': _dump(export_conflict_review_bundle(ConflictReviewExportRequest(output_path=args.output_path, language_ids=args.language_id, include_unreviewed_only=args.include_unreviewed_only))); return
    if args.cmd == 'list-conflict-exports': _dump(list_conflict_review_exports(limit=args.limit)); return
    if args.cmd == 'coverage-report': _dump(build_coverage_report(CoverageReportRequest(output_path=args.output_path, language_ids=args.language_id, include_runtime=not args.no_runtime, include_graph=not args.no_graph))); return
    if args.cmd == 'list-coverage-reports': _dump(list_coverage_reports(limit=args.limit)); return

    if args.cmd == 'upsert-phonology-profile': _dump(upsert_phonology_profile(args.language_id, args.notation_system, broad_ipa=args.broad_ipa, stress_policy=args.stress_policy, syllable_template=args.syllable_template, notes=args.notes)); return
    if args.cmd == 'list-phonology-profiles': _dump(list_phonology_profiles(language_id=args.language_id)); return
    if args.cmd == 'phonology-hint': _dump(phonology_hint(args.text, args.language_id)); return

    if args.cmd == 'build-implementation-matrix': _dump(build_implementation_matrix(output_path=args.output_path)); return
    if args.cmd == 'list-implementation-matrix-reports': _dump(list_implementation_matrix_reports(limit=args.limit)); return


    if args.cmd == 'self-fill-gap-scan': _dump(scan_self_fill_gaps(language_ids=args.language_id, stage_candidates=not args.no_stage)); return
    if args.cmd == 'list-self-fill-candidates': _dump(list_self_fill_candidates(status=args.status, language_id=args.language_id, surface_type=args.surface_type, limit=args.limit)); return
    if args.cmd == 'list-self-fill-scans': _dump(list_self_fill_scan_runs(limit=args.limit)); return
    if args.cmd == 'promote-self-fill-candidate': _dump(promote_self_fill_candidate(args.candidate_id, reviewer=args.reviewer)); return
    if args.cmd == 'reject-self-fill-candidate': _dump(reject_self_fill_candidate(args.candidate_id, reviewer=args.reviewer, notes=args.notes)); return
    if args.cmd == 'stage-iso-self-fill': _dump(stage_iso_fixture_candidates(args.path)); return
    if args.cmd == 'stage-glottolog-self-fill': _dump(stage_glottolog_fixture_candidates(args.path)); return
    if args.cmd == 'stage-cldr-self-fill': _dump(stage_cldr_fixture_candidates(args.path)); return
    if args.cmd == 'list-self-fill-import-runs': _dump(list_self_fill_import_runs(limit=args.limit)); return
    if args.cmd == 'list-self-fill-conflicts': _dump(list_self_fill_conflicts(status=args.status, limit=args.limit)); return
    if args.cmd == 'resolve-self-fill-conflict': _dump(resolve_self_fill_conflict(args.conflict_id, args.decision, notes=args.notes)); return
    if args.cmd == 'run-approved-self-fill-bootstrap': _dump(run_approved_source_import_bootstrap()); return
    if args.cmd == 'run-recurring-self-fill-release': _dump(run_recurring_self_fill_release(min_score=args.min_score, reviewer=args.reviewer, signing_key=args.signing_key)); return
    if args.cmd == 'list-self-fill-release-runs': _dump(list_self_fill_release_runs(limit=args.limit)); return
    if args.cmd == 'list-self-fill-release-artifacts': _dump(list_self_fill_release_artifacts(release_run_id=args.release_run_id, limit=args.limit)); return
    if args.cmd == 'run-scheduled-self-fill-release': _dump(run_scheduled_self_fill_release_cycle(schedule_kind=args.schedule_kind, min_score=args.min_score, reviewer=args.reviewer, signing_key=args.signing_key)); return
    if args.cmd == 'list-self-fill-retention-policies': _dump(list_self_fill_retention_policies(limit=args.limit)); return
    if args.cmd == 'list-self-fill-retention-actions': _dump(list_self_fill_retention_actions(limit=args.limit)); return
    if args.cmd == 'list-self-fill-rollback-index': _dump(list_self_fill_rollback_index(limit=args.limit)); return
    if args.cmd == 'build-self-fill-replay-manifest': _dump(build_self_fill_replay_manifest(rollback_id=args.rollback_id, release_run_id=args.release_run_id)); return
    if args.cmd == 'restore-self-fill-snapshot': _dump(restore_self_fill_snapshot(rollback_id=args.rollback_id, release_run_id=args.release_run_id, create_backup=not args.no_backup)); return
    if args.cmd == 'compact-self-fill-release': _dump(compact_self_fill_release(rollback_id=args.rollback_id, release_run_id=args.release_run_id)); return
    if args.cmd == 'list-self-fill-replay-runs': _dump(list_self_fill_replay_runs(limit=args.limit)); return
    if args.cmd == 'list-self-fill-compaction-actions': _dump(list_self_fill_compaction_actions(limit=args.limit)); return

    if args.cmd == 'plan-acquisition-job': _dump(plan_acquisition_job(AcquisitionJobRequest(corpus_name=args.corpus_name, stage_name=args.stage_name, output_dir=args.output_dir, notes=args.notes))); return
    if args.cmd == 'record-staged-asset': _dump(record_staged_asset(StagedAssetRequest(job_id=args.job_id, file_path=args.file_path, asset_kind=args.asset_kind, notes=args.notes))); return
    if args.cmd == 'validate-staged-asset': _dump(validate_staged_asset(ValidationReportRequest(file_path=args.file_path, expected_kind=args.expected_kind, expected_source_name=args.expected_source_name, notes=args.notes))); return
    if args.cmd == 'list-acquisition-jobs': _dump(list_acquisition_jobs(corpus_name=args.corpus_name)); return
    if args.cmd == 'list-validation-reports': _dump(list_validation_reports(limit=args.limit)); return
    if args.cmd == 'export-ingestion-workspace': _dump(export_ingestion_workspace(IngestionWorkspaceExportRequest(output_path=args.output_path, include_corpus_manifests=not args.no_corpus_manifests, include_import_runs=not args.no_import_runs, include_batch_runs=not args.no_batch_runs, include_validation_reports=not args.no_validation_reports, include_jobs=not args.no_jobs))); return
