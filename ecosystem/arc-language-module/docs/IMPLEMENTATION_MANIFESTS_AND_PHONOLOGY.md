# Implementation Manifests and Phonology — Current State (v0.24)

This document describes what is actually implemented versus what depends on external corpora or live backends.

## Implementation matrix

Run `python -m arc_lang.cli.main build-implementation-matrix` to generate a live report.
The report is stored in `implementation_matrix_reports` and can be listed with `list-implementation-matrix-reports`.

### Implemented entirely in-package (no external dependency)

| Surface | Status |
|---------|--------|
| Language graph (languages, scripts, lineage nodes/edges) | Fully implemented |
| Language aliases (endonym/exonym/romanized/autonym) | Fully implemented |
| Language variants (dialect/register/orthography/sociolect/historical) | Fully implemented |
| Custom lineage assertions + arbitration | Fully implemented |
| Language submission + governance review workflow | Fully implemented |
| Operator policy layer | Fully implemented |
| Source authority weights | Fully implemented |
| Provider registry + health snapshots | Fully implemented |
| Runtime receipts (translation, speech, action) | Fully implemented |
| Translation install plans | Fully implemented |
| Provider action catalogs | Fully implemented |
| Evidence export bundles | Fully implemented |
| Conflict review exports | Fully implemented |
| Coverage reports | Fully implemented |
| Implementation matrix reports | Fully implemented |
| Acquisition workspace (jobs, assets, validation, export) | Fully implemented |
| Batch import/export | Fully implemented |
| Semantic concept graph + concept links | Fully implemented |

### Seeded / partial (package-owned but limited coverage)

| Surface | Coverage | Notes |
|---------|----------|-------|
| Phrase translations | 35 languages × 11 canonical keys | Seeded from config; not a full translation corpus |
| Lexeme + etymology graph | Seed data for common words | Not a full lexical database |
| Phonology profiles | 12 languages | Broad IPA hints + stress/syllable info. Not full phonemic inventory. See below. |
| Transliteration profiles | 11 entries across 9 languages | Scheme-level metadata + example. Not a character-level mapping engine. |
| Pronunciation profiles | Seeded per language | Romanization scheme + IPA hint. Not a TTS phoneme set. |
| Local seeded translation | 35 languages | Phrase-match only; does not generalize |

### Requires external backend (explicitly not implemented)

| Surface | External requirement | Notes |
|---------|---------------------|-------|
| Argos Translate (local NMT) | `pip install argostranslate` + model download | Optional local backend. Not installed by default. |
| NLLB translation | NLLB model download + inference server | Bridge stub only. |
| PersonaPlex speech | NVIDIA PersonaPlex API key | Boundary stub only. |

## Phonology profiles — honest scope statement

Phonology profiles in this package are **broad hints**, not full phonemic inventories.

Each profile includes:
- `notation_system` (e.g., `broad_ipa`)
- `broad_ipa`: a representative IPA string for the language
- `stress_policy`: e.g., `lexical_stress`, `predictable_with_accents`, `tonal_five_tones`
- `syllable_template`: canonical syllable structure notation
- `examples`: a small dict of word → IPA hint pairs
- `notes`: explicit disclosure of what is and is not modeled

### Languages with phonology profiles (v0.24 seed)

English, Spanish, French, German, Russian, Hindi, Japanese, Korean, Mandarin Chinese,
Arabic (MSA), Turkish, Thai.

These 12 profiles were added in v0.24. All other seeded languages currently have `missing_phonology: true`
in coverage reports — this is the honest gap, not a silent omission.

### CLI commands

```
python -m arc_lang.cli.main upsert-phonology-profile lang:fra broad_ipa --broad-ipa "fʁɑ̃sɛ" --stress-policy phrase_final
python -m arc_lang.cli.main list-phonology-profiles --language-id lang:jpn
python -m arc_lang.cli.main phonology-hint "こんにちは" lang:jpn
```

## Transliteration profiles — honest scope statement

Transliteration profiles record:
- Which scheme is used (e.g., Hepburn, Revised Romanization of Korean, Pinyin)
- Coverage maturity: `none | seeded | experimental | reviewed | production`
- Example input/output pair
- Explicit notes on what the scheme does and does not cover

The package does **not** include a character-level transliteration engine. Profiles declare
what scheme applies and at what maturity; actual character mapping requires an external library
(e.g., `transliterate`, `Unidecode`) or a bundled table (not yet included).

### v0.24 transliteration profile coverage

| Language | Script | Target | Scheme | Coverage |
|----------|--------|--------|--------|----------|
| Russian | Cyrl | Latn | BGN/PCGN approx. | seeded |
| Cherokee | Cher | Latn | Syllabary chart | seeded |
| Hindi | Deva | Latn | Broad hint (not IAST) | experimental |
| Arabic | Arab | Latn | Broad hint (not ALA-LC) | experimental |
| Hebrew | Hebr | Latn | Broad hint (not ALA-LC) | experimental |
| Japanese | Hira | Latn | Modified Hepburn | seeded |
| Japanese | Kana | Latn | Modified Hepburn | seeded |
| Korean | Hang | Latn | Revised Romanization | experimental |
| Chinese | Hans | Latn | Pinyin (examples only) | experimental |
| Greek | Grek | Latn | ELOT 743 approx. | seeded |
| Thai | Thai | Latn | Paiboon approx. | experimental |

## Backend manifests

Backend manifests declare provider expectations at the package level:
- `execution_mode`: `local`, `optional_local`, `external_bridge`, `optional_external`
- `supported_pairs`: language pairs the provider can handle (if known)
- `dependency_json`: required packages or services
- `health_policy_json`: how health is assessed

These are operator-visible via `GET /backend-manifests` or `python -m arc_lang.cli.main system-status`.

## Corpus manifests

Corpus manifests declare what external corpora are needed and their acquisition status:
- `acquisition_status`: `installed` | `external_required` | `partial`
- `corpus_kind`: `genealogy` | `identifiers` | `scripts_locales` | `phrase_corpus`

Current manifest entries: Glottolog, ISO 639-3, CLDR, Common Seed (installed).
