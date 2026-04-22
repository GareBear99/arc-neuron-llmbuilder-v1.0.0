# Semantic Concepts, Variants, and Coverage — Current State (v0.24)

## Semantic concept graph

`semantic_concepts` + `concept_links` tables implement a lightweight universal meaning graph.

**30 concepts seeded** across 6 domains: `social`, `discourse`, `grammar`, `basic_vocabulary`, `time`, `colors`, `numerals`, `metalinguistic`.

Examples: `concept_greeting_hello`, `concept_gratitude_thanks`, `concept_affirmation_yes`, `concept_water`, `concept_sun`, `concept_language_speech`, `concept_translation`.

**3 concept→phrase_key links seeded** connecting `hello`, `thank_you`, and `what_is_this` phrase groups to their semantic concepts. These links propagate to all 34 language phrase translations automatically.

Operators can link concepts to lexemes, phrase keys, languages, or aliases:
```bash
python -m arc_lang.cli.main upsert-semantic-concept "water" --domain basic_vocabulary
python -m arc_lang.cli.main link-concept concept_water phrase_key water
python -m arc_lang.cli.main concept-bundle concept_greeting_hello
```

## Language variants

`language_variants` table. **37 entries seeded** for 12 languages, covering all 4 variant types:

- **dialect** — Castilian vs Latin American Spanish, European vs Brazilian Portuguese, Egyptian/Levantine/Gulf Arabic, Putonghua vs Guoyu Mandarin, etc.
- **register** — Formal written English, Informal spoken English, Japanese keigo (honorific)
- **orthography** — Cherokee Syllabics vs Cherokee Romanized, Modern Standard Arabic as orthographic standard
- **historical_stage** — Old English, Middle English, Classical Chinese (wenyan), Old Japanese, Church Slavonic

`mutual_intelligibility` values reflect scholarly estimates (0.0–1.0). Old English vs Modern English: 0.05. Latin American vs Castilian Spanish: 0.95.

```bash
python -m arc_lang.cli.main list-language-variants --language-id lang:eng
python -m arc_lang.cli.main list-language-variants --variant-type historical_stage
python -m arc_lang.cli.main upsert-language-variant lang:deu "Bavarian" dialect --region-hint DE-BY --mutual-intelligibility 0.7
```

## Coverage reports

Coverage reports (`build_coverage_report`) provide per-language assessments with:

- Alias counts by type (endonym/exonym/romanized/alias/autonym)
- Script count, lineage edge count, custom lineage assertion count
- Profile counts: phonology, transliteration, pronunciation
- Capability maturity summary dict
- 4 gap flags: `missing_phonology`, `missing_transliteration` (non-Latin only), `missing_pronunciation`, `missing_script`
- `has_non_latin_script` boolean

Aggregate summary includes: `with_phonology_profiles`, `with_transliteration_profiles`, `with_pronunciation_profiles`, `with_lineage_edges`, `with_variants`, `with_concepts`, `missing_*` counts.

As of v0.24: **all 4 gap flags are 0** across all 34 seeded languages.

```bash
python -m arc_lang.cli.main coverage-report --output-path coverage.json
python -m arc_lang.cli.main list-coverage-reports
```
