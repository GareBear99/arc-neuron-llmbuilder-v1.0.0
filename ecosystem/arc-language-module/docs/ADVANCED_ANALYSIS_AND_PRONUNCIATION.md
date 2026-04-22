# Advanced Analysis and Pronunciation — Current State (v0.24)

## What is implemented

`analyze_text` (service + CLI + API) performs:
- Script detection via Unicode codepoint ranges
- Tokenization (word-boundary regex, Unicode-aware)
- Per-token lexeme lookup against the seeded lexeme graph
- Phrase-level match against seeded phrase translations
- Transliteration (if source script is non-Latin and a profile exists)
- Pronunciation hint retrieval (if a pronunciation profile exists)
- Transliteration profile context listing for the detected/supplied language

`pronunciation_guide` (service + CLI + API) provides:
- IPA hint lookup from `pronunciation_profiles`
- Romanization scheme identification
- Example-based hint for known words
- Honest fallback: returns `ok: false` with `error: pronunciation_profile_not_found` when no profile exists

## Honest scope

This is a **seeded operator-assist layer**, not a full parser or phonology engine.

- Lexeme matching is exact seeded lookup. No stemming, no morphological analysis, no out-of-vocabulary handling.
- Pronunciation hints are broad approximations from `pronunciation_profiles`. They are not phoneme-level TTS inputs.
- Phonology profiles (`phonology_hint`) provide broad IPA, stress policy, and syllable template — not a full phonemic inventory.
- All 34 seeded languages have pronunciation and phonology profiles. All non-Latin-script languages have transliteration profiles.

## CLI

```bash
python -m arc_lang.cli.main analyze-text "こんにちは" --language-id lang:jpn
python -m arc_lang.cli.main pronounce "مرحبا" --language-id lang:arb
python -m arc_lang.cli.main phonology-hint "привет" lang:rus
python -m arc_lang.cli.main list-pronunciation-profiles --language-id lang:eng
python -m arc_lang.cli.main list-phonology-profiles --language-id lang:cmn
```

## API

- `GET /detect?text=...` — language detection
- `POST /translate-explain` — translate with etymology + pronunciation
- `GET /phonology/hint?text=...&language_id=...` — phonology hint
- `GET /phonology/profiles?language_id=...` — list phonology profiles
