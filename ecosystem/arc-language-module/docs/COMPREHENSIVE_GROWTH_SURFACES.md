# Comprehensive Growth Surfaces — Current State (v0.24)

All structural growth surfaces are implemented and governed. This document maps each to its current operational state.

## Alias and endonym management

`language_aliases` table stores governed aliases with `alias_type` (endonym/exonym/autonym/romanized/alias), `script_id`, `region_hint`, `source_name`, `confidence`. Searchable via both `search_languages` (queries both `aliases_json` seed column and the `language_aliases` table) and `list-language-aliases`.

79 aliases seeded across 35 languages. Operators can add via `upsert-language-alias`.

## Cross-lexeme relationship assertions

`relationship_assertions` table stores borrowing/cognate/calque/loan_translation/false_friend/derived_variant edges between lexemes with `confidence`, `disputed`, `source_name`, `source_ref`. Queryable and filterable by relation type.

0 seeded (requires scholarly linguistic data). Operators can assert via `assert-relationship`.

## Batch import/export

`batch_io_runs` table tracks all batch import and export operations with mode, object_type, path, dry_run, record_count, and status.

Supported object types for import: `language_submissions`, `custom_lineage`, `aliases`, `relationships`.
Supported for export: `languages`, `aliases`, `relationships`, `lineage_bundle`.

All batch operations support dry-run mode. CLI: `batch-import`, `batch-export`, `list-batch-runs`.

## Source authority weights

`source_weights` table stores per-source `authority_weight` values that directly feed into arbitration scoring. 7 sources seeded:

| Source | Weight |
|--------|--------|
| glottolog | 1.0 |
| iso639_3 | 0.9 |
| cldr | 0.85 |
| common_seed_local | 0.7 |
| common_seed | 0.6 |
| user_custom | 0.5 |
| user_submission | 0.45 |

Operator-updatable at runtime. Changes take effect on next `resolve_effective_lineage` call.

## Semantic concept graph

`semantic_concepts` + `concept_links` tables. 30 universal concepts seeded (greetings, discourse particles, basic vocabulary, time, colors, metalinguistic). Linked to phrase_translations via canonical_key. Operators can add concepts and link them to lexemes, phrases, or languages.

## Language variants

`language_variants` table. 104 dialect/register/orthography/historical_stage entries seeded across the seed set. `mutual_intelligibility` field (0.0–1.0) tracks cross-variant comprehensibility. All 4 variant types are operational.

## Conflict review exports

`conflict_review_exports` table records all operator conflict review bundles. Exports arbitrate effective lineage for each language and surface claims where margin < 0.2.

## Coverage reports

`coverage_reports` table stores all coverage report runs with output_path and summary JSON. Per-language output includes alias type breakdown, phonology/transliteration/pronunciation counts, lineage edge count, gap flags, and capability maturity summary.
