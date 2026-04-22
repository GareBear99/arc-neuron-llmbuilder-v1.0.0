from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScriptRecord(BaseModel):
    script_id: str = Field(min_length=3, max_length=8)
    name: str = Field(min_length=1, max_length=120)
    unicode_ranges: list[list[int]] = Field(default_factory=list)


class LineageNodeRecord(BaseModel):
    node_id: str = Field(min_length=5, max_length=64)
    node_type: str = Field(min_length=4, max_length=24)
    name: str = Field(min_length=1, max_length=160)
    parent_node_id: str | None = None
    source_name: str = 'common_seed'
    source_ref: str | None = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class LanguageRecord(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    iso639_3: str | None = Field(default=None, min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=160)
    family: str | None = None
    branch: str | None = None
    parent_language_id: str | None = None
    scripts: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    common_words: list[str] = Field(default_factory=list)
    source_name: str = 'common_seed'
    source_ref: str | None = None
    lineage_confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class DetectionResult(BaseModel):
    text: str
    top_script: str | None
    candidates: list[dict[str, Any]]
    winner_language_id: str | None
    confidence: float
    rationale: str


class TranslationExplainRequest(BaseModel):
    source_text: str
    source_language_id: str | None = None
    target_language_id: str
    translated_text: str
    provider: str = 'manual'
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ''


class TranslateExplainQuery(BaseModel):
    text: str
    target_language_id: str
    source_language_id: str | None = None
    allow_detect: bool = True


class SpeechRequest(BaseModel):
    text: str
    language_id: str
    voice_hint: str | None = None
    dry_run: bool = True


class ImportRequest(BaseModel):
    path: str = Field(min_length=1)


class SearchQuery(BaseModel):
    q: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class ManualLineageRequest(BaseModel):
    src_id: str = Field(min_length=3, max_length=64)
    dst_id: str = Field(min_length=3, max_length=64)
    relation: str = Field(min_length=3, max_length=64)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    disputed: bool = False
    source_name: str = 'user_custom'
    source_ref: str | None = None
    notes: str = ''
    status: str = 'user_asserted'


class LanguageSubmissionRequest(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    iso639_3: str | None = Field(default=None, min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=160)
    family: str | None = None
    branch: str | None = None
    parent_language_id: str | None = None
    aliases: list[str] = Field(default_factory=list)
    common_words: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)
    source_name: str = 'user_submission'
    source_ref: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    notes: str = ''
    status: str = 'submitted'


class ReviewDecisionRequest(BaseModel):
    target_type: str = Field(pattern='^(language_submission|custom_lineage)$')
    target_id: str = Field(min_length=3, max_length=64)
    decision: str = Field(pattern='^(needs_review|accepted_local|rejected|disputed)$')
    reviewer: str = Field(default='system_local', min_length=2, max_length=80)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    notes: str = ''


class CapabilityUpdateRequest(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    capability_name: str = Field(min_length=3, max_length=64)
    maturity: str = Field(pattern='^(none|seeded|experimental|reviewed|production)$')
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    provider: str = Field(default='local')
    notes: str = ''


class ArbitrationQuery(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)


class PolicyUpdateRequest(BaseModel):
    policy_key: str = Field(min_length=3, max_length=64)
    policy_value: str = Field(min_length=1, max_length=64)
    notes: str = ''


class EvidenceExportRequest(BaseModel):
    output_path: str = Field(min_length=1)
    language_ids: list[str] = Field(default_factory=list)
    include_receipts: bool = True
    include_runtime: bool = True
    include_graph: bool = True


class RuntimeTranslateRequest(BaseModel):
    text: str
    target_language_id: str
    source_language_id: str | None = None
    allow_detect: bool = True
    preferred_translation_provider: str | None = None
    require_speech: bool = False
    speech_provider: str | None = None
    voice_hint: str | None = None
    dry_run: bool = True


class RuntimeSpeechRequest(BaseModel):
    text: str
    language_id: str
    provider: str | None = None
    voice_hint: str | None = None
    dry_run: bool = True


class ProviderRegistrationRequest(BaseModel):
    provider_name: str = Field(min_length=2, max_length=64)
    provider_type: str = Field(pattern='^(translation|speech)$')
    enabled: bool = True
    local_only: bool = False
    notes: str = ''


class ProviderHealthRequest(BaseModel):
    provider_name: str = Field(min_length=2, max_length=64)
    status: str = Field(pattern='^(healthy|degraded|offline)$')
    latency_ms: int | None = Field(default=None, ge=0)
    error_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str = ''


class TranslationInstallPlanRequest(BaseModel):
    source_language_id: str = Field(min_length=5, max_length=64)
    target_language_id: str = Field(min_length=5, max_length=64)
    provider_name: str = Field(default='argos_local', min_length=2, max_length=64)
    notes: list[str] = Field(default_factory=list)


class BackendActionRequest(BaseModel):
    provider_name: str = Field(min_length=2, max_length=64)
    source_language_id: str = Field(min_length=5, max_length=64)
    target_language_id: str = Field(min_length=5, max_length=64)
    action_name: str | None = Field(default=None, min_length=2, max_length=64)
    dry_run: bool = True
    allow_mutation: bool = False
    package_ref: str | None = None
    notes: list[str] = Field(default_factory=list)


class PronunciationRequest(BaseModel):
    text: str
    language_id: str | None = Field(default=None, min_length=5, max_length=64)
    allow_detect: bool = True
    target_script: str = Field(default='Latn', min_length=3, max_length=8)


class AnalysisRequest(BaseModel):
    text: str
    language_id: str | None = Field(default=None, min_length=5, max_length=64)
    allow_detect: bool = True
    include_pronunciation: bool = True


class AliasUpsertRequest(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    alias: str = Field(min_length=1, max_length=160)
    alias_type: str = Field(pattern='^(alias|endonym|exonym|autonym|romanized)$')
    normalized_form: str | None = None
    script_id: str | None = Field(default=None, min_length=3, max_length=8)
    region_hint: str | None = None
    source_name: str = 'user_custom'
    source_ref: str | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    notes: str = ''


class RelationshipAssertionRequest(BaseModel):
    src_lexeme_id: str = Field(min_length=3, max_length=64)
    dst_lexeme_id: str = Field(min_length=3, max_length=64)
    relation: str = Field(pattern='^(borrowing|cognate|calque|loan_translation|false_friend|derived_variant)$')
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    disputed: bool = False
    source_name: str = 'user_custom'
    source_ref: str | None = None
    notes: str = ''


class BatchImportRequest(BaseModel):
    input_path: str = Field(min_length=1)
    object_type: str = Field(pattern='^(language_submissions|custom_lineage|aliases|relationships)$')
    dry_run: bool = True


class BatchExportRequest(BaseModel):
    output_path: str = Field(min_length=1)
    object_type: str = Field(pattern='^(languages|aliases|relationships|lineage_bundle)$')
    language_ids: list[str] = Field(default_factory=list)
    include_provenance: bool = True


class SourceWeightUpdateRequest(BaseModel):
    source_name: str = Field(min_length=2, max_length=80)
    authority_weight: float = Field(ge=0.0, le=2.0)
    notes: str = ''


class TransliterationRequest(BaseModel):
    text: str
    source_script: str | None = Field(default=None, min_length=3, max_length=8)
    target_script: str = Field(default='Latn', min_length=3, max_length=8)
    language_id: str | None = Field(default=None, min_length=5, max_length=64)
    allow_detect: bool = True


class TransliterationProfileUpsertRequest(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    source_script: str = Field(min_length=3, max_length=8)
    target_script: str = Field(default='Latn', min_length=3, max_length=8)
    scheme_name: str = Field(min_length=3, max_length=80)
    coverage: str = Field(pattern='^(none|seeded|experimental|reviewed|production)$')
    example_in: str | None = None
    example_out: str | None = None
    notes: str = ''


class SemanticConceptUpsertRequest(BaseModel):
    concept_id: str | None = Field(default=None, min_length=3, max_length=64)
    canonical_label: str = Field(min_length=1, max_length=160)
    domain: str = Field(default='general', min_length=2, max_length=64)
    description: str = ''
    source_name: str = 'user_custom'
    source_ref: str | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ConceptLinkRequest(BaseModel):
    concept_id: str = Field(min_length=3, max_length=64)
    target_type: str = Field(pattern='^(lexeme|language|phrase_key|alias)$')
    target_id: str = Field(min_length=1, max_length=160)
    relation: str = Field(default='expresses', min_length=3, max_length=64)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    notes: str = ''


class LanguageVariantUpsertRequest(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    variant_name: str = Field(min_length=1, max_length=160)
    variant_type: str = Field(pattern='^(dialect|register|orthography|sociolect|historical_stage)$')
    region_hint: str | None = None
    script_id: str | None = Field(default=None, min_length=3, max_length=8)
    status: str = Field(default='documented', pattern='^(documented|experimental|reviewed|deprecated)$')
    mutual_intelligibility: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str = ''


class ConflictReviewExportRequest(BaseModel):
    output_path: str = Field(min_length=1)
    language_ids: list[str] = Field(default_factory=list)
    include_unreviewed_only: bool = False


class CoverageReportRequest(BaseModel):
    output_path: str | None = None
    language_ids: list[str] = Field(default_factory=list)
    include_runtime: bool = True
    include_graph: bool = True


class AcquisitionJobRequest(BaseModel):
    corpus_name: str = Field(min_length=2, max_length=160)
    stage_name: str = Field(default='staging', min_length=2, max_length=64)
    output_dir: str | None = None
    notes: str = ''


class StagedAssetRequest(BaseModel):
    job_id: str = Field(min_length=3, max_length=64)
    file_path: str = Field(min_length=1)
    asset_kind: str = Field(default='unknown', min_length=2, max_length=64)
    notes: str = ''


class ValidationReportRequest(BaseModel):
    file_path: str = Field(min_length=1)
    expected_kind: str = Field(pattern='^(csv|json|zip|any)$')
    expected_source_name: str | None = None
    notes: str = ''


class IngestionWorkspaceExportRequest(BaseModel):
    output_path: str = Field(min_length=1)
    include_corpus_manifests: bool = True
    include_import_runs: bool = True
    include_batch_runs: bool = True
    include_validation_reports: bool = True
    include_jobs: bool = True


class PhonologyProfileUpsertRequest(BaseModel):
    language_id: str = Field(min_length=5, max_length=64)
    notation_system: str = Field(min_length=3, max_length=40)
    broad_ipa: str | None = None
    stress_policy: str | None = None
    syllable_template: str | None = None
    examples: dict[str, str] = Field(default_factory=dict)
    notes: str = ''
