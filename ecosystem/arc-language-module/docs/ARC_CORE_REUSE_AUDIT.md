# ARC Core Reuse Audit — v0.24

This document records the package's internal surface audit — what is fully implemented vs what stubs exist vs what depends on external components.

## Fully implemented (package-owned, no external dep)

| Surface | Tables | CLI | API |
|---------|--------|-----|-----|
| Language graph | languages, scripts, lineage_nodes, lineage_edges | ✓ | ✓ |
| Language aliases | language_aliases | ✓ | ✓ |
| Language variants | language_variants | ✓ | ✓ |
| Custom lineage | custom_lineage_assertions | ✓ | ✓ |
| Arbitration | reads lineage_edges + custom_lineage_assertions + source_weights | ✓ | ✓ |
| Governance/review | language_submissions, review_decisions | ✓ | ✓ |
| Language capabilities | language_capabilities | ✓ | ✓ |
| Phonology profiles | phonology_profiles | ✓ | ✓ |
| Pronunciation profiles | pronunciation_profiles | ✓ | ✓ |
| Transliteration profiles | transliteration_profiles | ✓ | ✓ |
| Semantic concepts | semantic_concepts, concept_links | ✓ | ✓ |
| Phrase translation | phrase_translations | ✓ | ✓ |
| Lexeme + etymology | lexemes, etymology_edges | ✓ | ✓ |
| Provider registry | provider_registry, provider_health | ✓ | ✓ |
| Runtime receipts | job_receipts, provider_action_receipts | ✓ | ✓ |
| Translation install plans | translation_install_plans | ✓ | ✓ |
| Provider action catalogs | — | ✓ | ✓ |
| Operator policy | operator_policies | ✓ | ✓ |
| Source weights | source_weights | ✓ | ✓ |
| Batch import/export | batch_io_runs | ✓ | ✓ |
| Evidence export | evidence_exports | ✓ | ✓ |
| Conflict review export | conflict_review_exports | ✓ | ✓ |
| Coverage reports | coverage_reports | ✓ | ✓ |
| Implementation matrix | implementation_matrix_reports | ✓ | ✓ |
| Acquisition workspace | acquisition_jobs, staged_assets, validation_reports | ✓ | ✓ |
| Ingestion workspace export | ingestion_workspace_exports | ✓ | ✓ |
| System status | — | ✓ | ✓ |

## Seeded/partial (package-owned, limited coverage)

| Surface | Coverage | Gap |
|---------|----------|-----|
| Phrase translations | 35 languages × 11 canonical keys | Seeded phrase coverage; not a full dictionary or corpus |
| Lexemes | 7 entries | Requires real lexical corpus for expansion |
| Etymology edges | 1 edge | Requires real etymological data |
| Relationship assertions | 0 seeded | Requires scholarly linguistic data |
| Concept links | 3 seeded | Expanding requires manual curation or corpus |
| Local seeded translation | Phrase-match only | Does not generalize to arbitrary text |

## Boundary stubs (external runtime required)

| Surface | External requirement | Package provides |
|---------|---------------------|-----------------|
| Argos local translation | argostranslate + models | Full adapter with dependency check |
| Argos bridge | External Argos runtime | Boundary stub with dry-run |
| NLLB bridge | NLLB model server | Boundary stub with dry-run |
| PersonaPlex speech | NVIDIA API | Boundary stub adapter |

## ISO runtime code map

`ISO6393_TO_RUNTIME` maps seeded ISO 639-3 codes to Argos/runtime codes. 31 entries covering all seeded languages. Low-resource languages (nav, chr, crk) are mapped but noted as lacking known Argos package support.
