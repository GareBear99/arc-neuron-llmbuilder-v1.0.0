# ARC Language Module — Architecture (v0.24.0)

## Core separation of concerns

| Concept | Separated from | Why it matters |
|---------|---------------|----------------|
| Language | Script | A language can be written in multiple scripts (Serbian: Cyrl+Latn). Script ≠ language. |
| Language | Locale | A locale (e.g. `en-US`) bundles language + region. The graph stores language; locales are external. |
| Genealogy | Software identifier | Glottolog genealogy ≠ ISO 639-3 code ≠ BCP 47 tag. All three are tracked but kept separate. |
| Translation equivalence | Etymological relatedness | Two words can be translations without being cognates; cognates can be false friends. |
| Pronunciation hint | Phonology truth | `pronunciation_profiles` give romanization/stress hints. `phonology_profiles` give broader IPA and syllable structure. Neither is a full phoneme inventory. |
| Text translation | Speech playback | The translation routing layer and the speech routing layer are separate services with separate provider registries and receipts. |
| Package-owned data | External corpus dependency | Every corpus is declared in `corpus_manifests` with `acquisition_status`. The package never silently assumes corpus data is available. |
| Canonical lineage | Custom assertions | `lineage_edges` hold source-backed graph truth. `custom_lineage_assertions` hold operator/user overrides. Arbitration resolves between them explicitly. |
| Graph truth | Runtime capability | Knowing a language exists in the graph does not mean the runtime can translate it. Capability maturity is tracked separately in `language_capabilities`. |

---

## Current state (v0.24.0)

| Surface | Count |
|---------|-------|
| Languages seeded | 35 (14 families, 20 branches) |
| Phrase translations | 385 (11 canonical keys × 35 languages, 2 registers) |
| Lexemes | 96 |
| Etymology edges | 36 (cognate, borrowing, false_friend, descends_from) |
| Language variants | 104 (dialect, register, orthography, historical_stage) |
| Phonology profiles | 35 (all seeded languages) |
| Pronunciation profiles | 35 (all seeded languages) |
| Transliteration profiles | 21 (all non-Latin-script languages) |
| Semantic concepts | 30 |
| Concept links | 46 |
| Tests | 325 passing, 0 failures, 28 test files |

---

## Layer map

```
┌─────────────────────────────────────────────────────────────┐
│  CLI (arc_lang.cli.main)   │  API (arc_lang.api.routes)     │
│  81 commands with help=    │  86 routes, FastAPI             │
├─────────────────────────────────────────────────────────────┤
│                     Service layer (40 modules)               │
│  seed_ingest  importers  onboarding  governance              │
│  arbitration  lineage  aliases  variants  concepts           │
│  phonology  transliteration  pronunciation                   │
│  orchestration  translation_backends  speech_provider        │
│  backend_diagnostics  package_lifecycle  provider_actions    │
│  coverage  conflict_review  evidence_export  manifests       │
│  acquisition_workspace  batch_io  system_status  search      │
│  detection  linguistic_analysis  translate_explain           │
│  etymology  relationships  source_policy  policy             │
│  stats  runtime_receipts  provider_registry                  │
├─────────────────────────────────────────────────────────────┤
│  Core (arc_lang.core)                                        │
│  db.py — SQLite WAL, runs all sql/*.sql migrations           │
│  config.py — all path constants                              │
│  models.py — Pydantic request/response types (359 lines)     │
├─────────────────────────────────────────────────────────────┤
│  SQLite database (data/arc_language.db)                      │
│  41 tables, WAL mode, 101 indexes (001_init + 002_indexes)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Arbitration

When canonical lineage edges and custom lineage assertions compete, `resolve_effective_lineage` scores every claim:

```
effective_score = confidence × source_weight(DB) × status_weight × decision_weight × dispute_factor
```

- `source_weight` — loaded from `source_weights` DB table. Seeded defaults: glottolog=1.0, iso639_3=0.9, cldr=0.85, common_seed=0.6. **Operator-updatable via `set-source-weight` — changes take effect on the next call, no restart needed.**
- `status_weight` — `canonical`=1.0, `accepted_local`=1.0, `user_asserted`=0.65, `disputed`=0.45, `rejected`=0.15
- `decision_weight` — based on latest governance review decision
- Claims with margin < 0.2 within the same relation bucket are flagged as conflicts

---

## Provider model

Providers are declared in `provider_registry`. Runtime routing in `orchestration.py` checks:
1. Capability maturity for the language pair (`language_capabilities`)
2. Provider health (`provider_health`) — 10 providers seeded: local ones healthy, bridge stubs offline
3. Operator policy (`operator_policies`) — 4 defaults: `allow_external_providers`, `allow_live_speech`, `allow_mutation_actions`, `runtime_default_dry_run`

Providers that fail any condition are blocked with an explicit error and a job receipt — never silently skipped.

Current providers: `local_seed` (healthy), `local_detect` (healthy), `local_graph` (healthy), `local_map` (healthy), `mirror_mock` (healthy), `argos_local` (degraded — optional), `argos_bridge` (offline stub), `nllb_bridge` (offline stub), `disabled` (healthy — explicit sink), `personaplex` (offline stub).

---

## Data flow: corpus ingestion

```
External corpus file
       ↓
import_glottolog_csv / import_iso639_csv / import_cldr_json
  dry_run=True  → parse + conflict-detect, no writes
  dry_run=False → upsert + provenance + import_run receipt
       ↓
languages + lineage_nodes + lineage_edges + language_scripts
       ↓
provenance_records  (source_name, confidence, notes per record)
import_runs  (seen, inserted, updated, conflict_count)
       ↓
[operator reviews conflicts via export-conflict-review]
       ↓
resolve_effective_lineage  (arbitration with live DB source weights)
```

---

## Schema: 41 tables

**Language graph:** `languages`, `scripts`, `language_scripts`, `lineage_nodes`, `lineage_edges`

**Lexical layer:** `lexemes`, `phrase_translations`, `etymology_edges`, `relationship_assertions`, `translation_assertions`

**Aliases and variants:** `language_aliases`, `language_variants`

**Concepts:** `semantic_concepts`, `concept_links`

**Linguistic profiles:** `pronunciation_profiles`, `phonology_profiles`, `transliteration_profiles`

**Governance:** `language_submissions`, `custom_lineage_assertions`, `review_decisions`, `language_capabilities`

**Provenance:** `provenance_records`, `import_runs`, `batch_io_runs`, `source_weights`

**Runtime:** `provider_registry`, `provider_health`, `job_receipts`, `provider_action_receipts`, `translation_install_plans`

**Policy:** `operator_policies`

**Manifests and matrix:** `backend_manifests`, `corpus_manifests`, `implementation_matrix_reports`

**Acquisition:** `acquisition_jobs`, `staged_assets`, `validation_reports`

**Exports:** `evidence_exports`, `conflict_review_exports`, `coverage_reports`, `ingestion_workspace_exports`

---

## SQL migrations

| File | Purpose |
|------|---------|
| `sql/001_init.sql` | Full schema: all 41 tables with primary indexes |
| `sql/002_indexes.sql` | 22 composite performance indexes for common query patterns |

`init_db()` runs all `sql/*.sql` files in alphabetical order. Safe to re-run: all statements use `IF NOT EXISTS` / `ON CONFLICT IGNORE`.

---

## External dependencies (all explicitly declared)

| Provider | Kind | Acquisition |
|----------|------|-------------|
| Glottolog corpus | `external_required` | glottolog.org — CC Attribution 4.0 |
| ISO 639-3 corpus | `external_required` | sil.org — free non-commercial |
| CLDR corpus | `external_required` | unicode.org — Unicode License |
| argostranslate + models | `optional_local` | `pip install argostranslate` + model download |
| NLLB model server | `external_bridge` | Bridge stub — no live runtime |
| PersonaPlex API | `optional_external` | NVIDIA API — boundary stub |
