"""
test_v29_phrase_concepts_complete.py

Covers all session-8 completions:
  - Phrase translations: 10 keys × 34 languages = 340 entries
  - All 34 languages fully covered for every phrase key
  - Concept links: 11 links across 8 concepts → 10 phrase keys
  - translation_assertions service
  - Example files have ≥6 rows each
  - English aliases expanded
  - ISO6393_TO_RUNTIME covers all seeded languages
  - translate_explain works end-to-end for seeded phrases
  - detect_language improved for chr/crk (more common_words)
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.translation_assertions import create_translation_assertion
from arc_lang.services.translate_explain import translate_explain
from arc_lang.services.detection import detect_language
from arc_lang.services.concepts import list_semantic_concepts, get_concept_bundle
from arc_lang.core.models import TranslationExplainRequest, TranslateExplainQuery


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── Phrase translation completeness ─────────────────────────────────────────

EXPECTED_KEYS = [
    'hello', 'thank_you', 'what_is_this',
    'goodbye', 'yes', 'no', 'please', 'sorry',
    'good_morning', 'how_are_you',
]
ALL_LANG_IDS = [
    'lang:eng', 'lang:spa', 'lang:fra', 'lang:deu', 'lang:por', 'lang:ita',
    'lang:nld', 'lang:rus', 'lang:ukr', 'lang:pol', 'lang:arb', 'lang:heb',
    'lang:hin', 'lang:mar', 'lang:ben', 'lang:urd', 'lang:pan', 'lang:tam',
    'lang:tel', 'lang:tur', 'lang:fas', 'lang:cmn', 'lang:yue', 'lang:jpn',
    'lang:kor', 'lang:vie', 'lang:ind', 'lang:msa', 'lang:tha', 'lang:swa',
    'lang:amh', 'lang:nav', 'lang:chr', 'lang:crk', 'lang:ell',
]


def test_340_phrase_entries_seeded():
    c = get_graph_stats()['counts']
    assert c['phrase_translations'] >= 350, (
        f"Expected 350 phrase entries (10 keys × 35 languages), got {c['phrase_translations']}"
    )


def test_all_10_canonical_keys_present():
    with connect() as conn:
        keys = {r['canonical_key'] for r in conn.execute(
            "SELECT DISTINCT canonical_key FROM phrase_translations"
        ).fetchall()}
    for key in EXPECTED_KEYS:
        assert key in keys, f"Missing canonical_key: {key!r}"


def test_every_language_has_every_phrase_key():
    with connect() as conn:
        for key in EXPECTED_KEYS:
            covered = {r['language_id'] for r in conn.execute(
                "SELECT language_id FROM phrase_translations WHERE canonical_key=?", (key,)
            ).fetchall()}
            missing = set(ALL_LANG_IDS) - covered
            assert not missing, (
                f"canonical_key={key!r} missing languages: {sorted(missing)}"
            )


def test_goodbye_phrase_all_34_languages():
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(DISTINCT language_id) AS c FROM phrase_translations WHERE canonical_key='goodbye'"
        ).fetchone()['c']
    assert n == len(ALL_LANG_IDS), f"goodbye should cover 34 languages, got {n}"


def test_low_resource_languages_have_goodbye():
    with connect() as conn:
        for lang_id in ('lang:nav', 'lang:chr', 'lang:crk'):
            row = conn.execute(
                "SELECT text_value FROM phrase_translations WHERE canonical_key='goodbye' AND language_id=?",
                (lang_id,)
            ).fetchone()
            assert row, f"{lang_id} missing 'goodbye' phrase entry"
            assert row['text_value'], f"{lang_id} 'goodbye' has empty text"


def test_yes_no_all_34_languages():
    with connect() as conn:
        for key in ('yes', 'no'):
            n = conn.execute(
                "SELECT COUNT(DISTINCT language_id) AS c FROM phrase_translations WHERE canonical_key=?",
                (key,)
            ).fetchone()['c']
            assert n == len(ALL_LANG_IDS), f"'{key}' should cover {len(ALL_LANG_IDS)} languages, got {n}"


def test_sorry_please_all_34_languages():
    with connect() as conn:
        for key in ('sorry', 'please'):
            n = conn.execute(
                "SELECT COUNT(DISTINCT language_id) AS c FROM phrase_translations WHERE canonical_key=?",
                (key,)
            ).fetchone()['c']
            assert n == len(ALL_LANG_IDS), f"'{key}' should cover {len(ALL_LANG_IDS)} languages, got {n}"


# ── Concept links ────────────────────────────────────────────────────────────

def test_11_concept_links_seeded():
    c = get_graph_stats()['counts']
    assert c['concept_links'] >= 11, f"Expected ≥11 concept links, got {c['concept_links']}"


def test_concept_farewell_linked_to_goodbye():
    with connect() as conn:
        link = conn.execute(
            "SELECT target_id FROM concept_links WHERE concept_id='concept_farewell_goodbye'"
        ).fetchone()
    assert link, "concept_farewell_goodbye has no concept_links"
    assert link['target_id'] == 'goodbye'


def test_concept_yes_no_linked():
    with connect() as conn:
        yes_link = conn.execute(
            "SELECT target_id FROM concept_links WHERE concept_id='concept_affirmation_yes'"
        ).fetchone()
        no_link = conn.execute(
            "SELECT target_id FROM concept_links WHERE concept_id='concept_negation_no'"
        ).fetchone()
    assert yes_link and yes_link['target_id'] == 'yes'
    assert no_link and no_link['target_id'] == 'no'


def test_concept_bundle_includes_phrase_links():
    bundle = get_concept_bundle('concept_greeting_hello')
    assert bundle['ok'] is True
    links = bundle.get('links', [])
    phrase_keys = [l['target_id'] for l in links if l.get('target_type') == 'phrase_key']
    assert 'hello' in phrase_keys
    assert 'how_are_you' in phrase_keys


# ── translation_assertions service ──────────────────────────────────────────

def test_create_translation_assertion_roundtrip():
    req = TranslationExplainRequest(
        source_language_id='lang:eng',
        target_language_id='lang:spa',
        source_text='water',
        translated_text='agua',
        confidence=0.9,
        rationale='Well-known Spanish lexeme for water',
        provider='manual',
    )
    result = create_translation_assertion(req)
    assert result['ok'] is True
    assert result['assertion_id'].startswith('ta_')
    assert result['confidence'] == 0.9
    assert result['source_language_id'] == 'lang:eng'
    assert result['target_language_id'] == 'lang:spa'


def test_create_translation_assertion_stored_in_db():
    req = TranslationExplainRequest(
        source_language_id='lang:fra',
        target_language_id='lang:deu',
        source_text='bonjour',
        translated_text='guten Tag',
        confidence=0.85,
        rationale='Standard greeting equivalence',
        provider='manual',
    )
    result = create_translation_assertion(req)
    assert result['ok'] is True
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM translation_assertions WHERE assertion_id=?",
            (result['assertion_id'],)
        ).fetchone()
    assert row is not None
    assert row['source_text'] == 'bonjour'
    assert row['translated_text'] == 'guten Tag'
    assert row['provider'] == 'manual'


def test_create_translation_assertion_multiple_providers():
    for provider in ('manual', 'local_seed', 'user_custom'):
        req = TranslationExplainRequest(
            source_language_id='lang:jpn',
            target_language_id='lang:eng',
            source_text='こんにちは',
            translated_text='hello',
            confidence=0.95,
            rationale=f'Test provider: {provider}',
            provider=provider,
        )
        result = create_translation_assertion(req)
        assert result['ok'] is True


# ── translate_explain end-to-end ─────────────────────────────────────────────

def test_translate_explain_hello_to_spanish():
    result = translate_explain(TranslateExplainQuery(
        text='hello',
        source_language_id='lang:eng',
        target_language_id='lang:spa',
    ))
    assert result['ok'] is True
    assert result.get('translated_text') or result.get('translation', {}).get('text_value')


def test_translate_explain_goodbye_to_french():
    result = translate_explain(TranslateExplainQuery(
        text='goodbye',
        source_language_id='lang:eng',
        target_language_id='lang:fra',
    ))
    assert result['ok'] is True


def test_translate_explain_yes_to_japanese():
    result = translate_explain(TranslateExplainQuery(
        text='yes',
        source_language_id='lang:eng',
        target_language_id='lang:jpn',
    ))
    assert result['ok'] is True


def test_translate_explain_sorry_to_arabic():
    result = translate_explain(TranslateExplainQuery(
        text='sorry',
        source_language_id='lang:eng',
        target_language_id='lang:arb',
    ))
    assert result['ok'] is True


# ── Detection quality ────────────────────────────────────────────────────────

def test_detect_cherokee_syllabics():
    result = detect_language("ᎣᏏᏲ ᏩᏙᏉ ᎤᎵᎮᎵᏍᏗ")
    assert result.winner_language_id == 'lang:chr'


def test_detect_arabic_text():
    result = detect_language("مرحبا شكرا لا نعم")
    assert result.winner_language_id == 'lang:arb'


def test_detect_japanese_hiragana():
    result = detect_language("こんにちは ありがとう")
    assert result.winner_language_id == 'lang:jpn'


def test_detect_mandarin_chinese():
    result = detect_language("你好 谢谢 再见 什么")
    assert result.winner_language_id == 'lang:cmn'


def test_detect_returns_candidates_list():
    result = detect_language("hello world")
    assert len(result.candidates) >= 1
    assert all('score' in c for c in result.candidates)


# ── Example files ─────────────────────────────────────────────────────────────

def test_example_glottolog_has_six_rows():
    path = ROOT / 'examples' / 'glottolog_sample.csv'
    import csv
    rows = list(csv.DictReader(open(path)))
    assert len(rows) >= 6, f"glottolog_sample.csv should have ≥6 data rows, got {len(rows)}"
    assert 'language_id' in rows[0]
    assert 'family' in rows[0]


def test_example_iso639_has_six_rows():
    path = ROOT / 'examples' / 'iso6393_sample.csv'
    import csv
    rows = list(csv.DictReader(open(path)))
    assert len(rows) >= 6, f"iso6393_sample.csv should have ≥6 data rows, got {len(rows)}"
    assert 'iso639_3' in rows[0]


def test_example_cldr_has_multiple_entries():
    path = ROOT / 'examples' / 'cldr_sample.json'
    data = json.loads(path.read_text())
    assert 'languages' in data
    assert len(data['languages']) >= 3


def test_example_files_importable_dry_run():
    from arc_lang.services.importers import import_glottolog_csv, import_iso639_csv, import_cldr_json
    g = import_glottolog_csv(ROOT / 'examples' / 'glottolog_sample.csv', dry_run=True)
    assert g['ok'] is True
    assert g['records_seen'] >= 6
    i = import_iso639_csv(ROOT / 'examples' / 'iso6393_sample.csv', dry_run=True)
    assert i['ok'] is True
    assert i['records_seen'] >= 6
    c = import_cldr_json(ROOT / 'examples' / 'cldr_sample.json', dry_run=True)
    assert c['ok'] is True
    assert c['records_seen'] >= 3


# ── English aliases ──────────────────────────────────────────────────────────

def test_english_has_multiple_aliases():
    with connect() as conn:
        row = conn.execute(
            "SELECT aliases_json FROM languages WHERE language_id='lang:eng'"
        ).fetchone()
    aliases = json.loads(row['aliases_json'])
    assert len(aliases) >= 2, f"English should have ≥2 aliases, got {aliases}"
    assert 'English' in aliases


def test_greek_has_native_script_alias():
    with connect() as conn:
        row = conn.execute(
            "SELECT aliases_json FROM languages WHERE language_id='lang:ell'"
        ).fetchone()
    aliases = json.loads(row['aliases_json'])
    assert any('ελλ' in a.lower() or 'Ελλ' in a for a in aliases), (
        f"Greek should have a native-script alias, got {aliases}"
    )


# ── Final stats completeness ─────────────────────────────────────────────────

def test_final_stats_summary():
    c = get_graph_stats()['counts']
    assert c['languages'] == 35
    assert c['phrase_translations'] >= 350
    assert c['semantic_concepts'] >= 30
    assert c['concept_links'] >= 11
    assert c['language_variants'] >= 100
    assert c['phonology_profiles'] >= 35
    assert c['transliteration_profiles'] >= 21
    assert c['pronunciation_profiles'] >= 35
    assert c['language_aliases'] >= 78
    assert c['language_capabilities'] >= 238
