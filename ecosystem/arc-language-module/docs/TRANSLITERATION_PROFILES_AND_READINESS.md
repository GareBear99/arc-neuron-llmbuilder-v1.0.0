# Transliteration Profiles and Readiness — Current State (v0.24)

## What is implemented

`transliteration_profiles` table stores per-language, per-script-pair transliteration metadata as first-class records. 21 profiles seeded covering all non-Latin-script languages in the seed.

Each profile records:
- `language_id`, `source_script`, `target_script` — what is being transliterated
- `scheme_name` — the named romanization scheme (e.g., Hepburn, Revised Romanization, Pinyin, BGN/PCGN)
- `coverage` — honest maturity: `none | seeded | experimental | reviewed | production`
- `example_in`, `example_out` — a concrete example pair
- `notes` — explicit scope statement (what the scheme does and does not cover)

## Seeded profiles (v0.24)

| Language | Source Script | Scheme | Coverage |
|----------|--------------|--------|----------|
| Russian | Cyrl | BGN/PCGN approx. | seeded |
| Ukrainian | Cyrl | BGN/PCGN approx. | seeded |
| Hindi | Deva | Broad hint (not IAST) | experimental |
| Marathi | Deva | Broad hint | experimental |
| Bengali | Beng | Broad hint | experimental |
| Punjabi | Guru | Broad hint | experimental |
| Tamil | Taml | Broad hint | experimental |
| Telugu | Telu | Broad hint | experimental |
| Arabic | Arab | Broad hint (not ALA-LC) | experimental |
| Persian | Arab | Broad hint | experimental |
| Urdu | Arab | Broad hint (Nastaliq) | experimental |
| Hebrew | Hebr | Broad hint | experimental |
| Japanese (Hiragana) | Hira | Modified Hepburn | seeded |
| Japanese (Katakana) | Kana | Modified Hepburn | seeded |
| Korean | Hang | Revised Romanization | experimental |
| Mandarin Chinese | Hans | Pinyin (examples only) | experimental |
| Cantonese | Hant | Jyutping (examples only) | experimental |
| Thai | Thai | Paiboon approx. | experimental |
| Amharic | Ethi | Broad Ge'ez hint | experimental |
| Greek | Grek | ELOT 743 approx. | seeded |
| Cherokee | Cher | Syllabary chart | seeded |

## What transliteration profiles do NOT provide

Profiles are **scheme declarations**, not **character-mapping engines**. The `transliterate()` function uses heuristic character-table lookups (Cyrillic→Latin) or returns the example pair for unseen inputs. A full production transliteration engine (e.g., ICU, `transliterate` Python library) must be wired externally.

Latin-script-only languages (Spanish, French, Indonesian, etc.) correctly report `missing_transliteration: false` in coverage reports — transliteration is not applicable to them.

## CLI

```bash
python -m arc_lang.cli.main list-transliteration-profiles --language-id lang:jpn
python -m arc_lang.cli.main transliterate "привет" Cyrl Latn
python -m arc_lang.cli.main upsert-transliteration-profile lang:vie Latn Latn viqr experimental
```

## Capability maturity

Languages with transliteration profiles have their `transliteration` capability set to `seeded` or `experimental` depending on profile coverage. This feeds into the runtime readiness matrix and install plans.
