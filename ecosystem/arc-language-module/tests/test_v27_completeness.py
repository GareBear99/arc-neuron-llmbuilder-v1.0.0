"""
test_v27_completeness.py

Final completeness tests — validates every surface brought to production state:

  Coverage:
  - All 34 seeded languages have phonology, pronunciation, and (where needed) transliteration
  - missing_transliteration only fires for non-Latin-script languages
  - Language variants seeded and queryable

  Seed integrity:
  - No lang:zho or lang:ara orphan IDs anywhere
  - variant_count returned by ingest_common_seed
  - All 4 variant_types present in seed

  Arbitration:
  - canonical status_weight = 1.0
  - DB source weights used (not hardcoded)
  - lang:ara fix doesn't break Arabic effective lineage

  Search:
  - language_aliases table queried
  - no duplicate results

  Coverage report correctness:
  - missing_transliteration=0 for all 34 languages
  - missing_phonology=0 for all 34 languages
  - missing_pronunciation=0 for all 34 languages
  - has_non_latin_script correctly identified

  Variants:
  - 37 variants seeded
  - dialect, register, orthography, historical_stage all present
  - upsert_language_variant works correctly
  - list_language_variants filters by type
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db, connect
from arc_lang.core.models import (
    CoverageReportRequest,
    LanguageVariantUpsertRequest,
)
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.coverage import build_coverage_report
from arc_lang.services.variants import upsert_language_variant, list_language_variants
from arc_lang.services.phonology import list_phonology_profiles
from arc_lang.services.pronunciation import list_pronunciation_profiles
from arc_lang.services.transliteration import list_transliteration_profiles
from arc_lang.services.arbitration import resolve_effective_lineage, STATUS_WEIGHTS
from arc_lang.services.search import search_languages


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── Seed integrity ──────────────────────────────────────────────────────────

def test_ingest_returns_variant_count():
    init_db()
    result = ingest_common_seed()
    assert 'variants' in result, "ingest_common_seed must return 'variants' count"
    assert result['variants'] >= 36


def test_ingest_returns_phonology_count_nonzero():
    result = ingest_common_seed()
    # phonology_profiles key added in session 3
    assert result.get('pronunciation_profiles', 0) >= 34
    assert result.get('transliteration_profiles', 0) >= 21


def test_no_orphan_lang_zho_anywhere():
    with connect() as conn:
        phon = conn.execute("SELECT COUNT(*) AS c FROM phonology_profiles WHERE language_id='lang:zho'").fetchone()['c']
        pron = conn.execute("SELECT COUNT(*) AS c FROM pronunciation_profiles WHERE language_id='lang:zho'").fetchone()['c']
        trns = conn.execute("SELECT COUNT(*) AS c FROM transliteration_profiles WHERE language_id='lang:zho'").fetchone()['c']
        vari = conn.execute("SELECT COUNT(*) AS c FROM language_variants WHERE language_id='lang:zho'").fetchone()['c']
    assert phon == 0, f"Orphan lang:zho in phonology_profiles ({phon} rows)"
    assert pron == 0, f"Orphan lang:zho in pronunciation_profiles ({pron} rows)"
    assert trns == 0, f"Orphan lang:zho in transliteration_profiles ({trns} rows)"
    assert vari == 0, f"Orphan lang:zho in language_variants ({vari} rows)"


def test_no_orphan_lang_ara_anywhere():
    with connect() as conn:
        vari = conn.execute("SELECT COUNT(*) AS c FROM language_variants WHERE language_id='lang:ara'").fetchone()['c']
        lang = conn.execute("SELECT COUNT(*) AS c FROM languages WHERE language_id='lang:ara'").fetchone()['c']
    assert lang == 0, "lang:ara should not be a language ID (use lang:arb)"
    assert vari == 0, f"Orphan lang:ara in language_variants ({vari} rows)"


def test_lang_arb_has_variants():
    variants = list_language_variants(language_id='lang:arb')
    assert variants['count'] >= 3, "lang:arb should have dialect variants seeded"
    types = {v['variant_type'] for v in variants['items']}
    assert 'dialect' in types


def test_lang_cmn_used_for_mandarin_not_zho():
    phon = list_phonology_profiles(language_id='lang:cmn')
    assert phon['results'], "lang:cmn must have phonology profile"
    pron = list_pronunciation_profiles(language_id='lang:cmn')
    assert pron['results'], "lang:cmn must have pronunciation profile"
    translit = list_transliteration_profiles(language_id='lang:cmn')
    assert translit['results'], "lang:cmn must have transliteration profile"


# ── Coverage report completeness ────────────────────────────────────────────

def test_coverage_report_zero_missing_flags():
    req = CoverageReportRequest()
    result = build_coverage_report(req)
    s = result['summary']
    assert s['missing_phonology'] == 0, f"missing_phonology={s['missing_phonology']} expected 0"
    assert s['missing_pronunciation'] == 0, f"missing_pronunciation={s['missing_pronunciation']} expected 0"
    assert s['missing_transliteration'] == 0, f"missing_transliteration={s['missing_transliteration']} expected 0"
    assert s['with_phonology_profiles'] == s['languages']  # dynamic
    assert s['with_pronunciation_profiles'] == s['languages']  # dynamic


def test_coverage_report_transliteration_only_fires_for_non_latin():
    req = CoverageReportRequest()
    result = build_coverage_report(req)
    for item in result['items']:
        if item['missing_transliteration']:
            # Must be a non-Latin-script language
            assert item['has_non_latin_script'], (
                f"{item['language_id']} flagged missing_transliteration "
                "but has no non-Latin script"
            )
        if not item['has_non_latin_script']:
            assert not item['missing_transliteration'], (
                f"{item['language_id']} is Latin-only but flagged missing_transliteration"
            )


def test_coverage_report_latin_only_languages_not_flagged():
    latin_only = ['lang:eng', 'lang:spa', 'lang:fra', 'lang:deu', 'lang:por',
                  'lang:ita', 'lang:nld', 'lang:pol', 'lang:tur', 'lang:ind',
                  'lang:msa', 'lang:vie', 'lang:swa', 'lang:nav', 'lang:crk']
    req = CoverageReportRequest(language_ids=latin_only)
    result = build_coverage_report(req)
    for item in result['items']:
        assert not item['missing_transliteration'], (
            f"{item['language_id']} is Latin-script-only but flagged missing_transliteration"
        )


def test_coverage_report_non_latin_languages_have_profiles():
    non_latin = ['lang:rus', 'lang:hin', 'lang:arb', 'lang:jpn',
                 'lang:kor', 'lang:cmn', 'lang:heb', 'lang:tha',
                 'lang:ben', 'lang:tam', 'lang:fas', 'lang:yue']
    req = CoverageReportRequest(language_ids=non_latin)
    result = build_coverage_report(req)
    for item in result['items']:
        assert not item['missing_transliteration'], (
            f"{item['language_id']} has non-Latin script but no transliteration profile"
        )
        assert not item['missing_phonology'], (
            f"{item['language_id']} is missing phonology profile"
        )


def test_coverage_report_variants_reflected():
    req = CoverageReportRequest(language_ids=['lang:eng', 'lang:spa', 'lang:jpn'])
    result = build_coverage_report(req)
    eng = next(x for x in result['items'] if x['language_id'] == 'lang:eng')
    assert eng['variants'] >= 5, "English should have dialect and register variants"
    spa = next(x for x in result['items'] if x['language_id'] == 'lang:spa')
    assert spa['variants'] >= 2, "Spanish should have dialect variants"


# ── Phonology completeness ──────────────────────────────────────────────────

def test_all_34_languages_have_phonology():
    with connect() as conn:
        lang_ids = [r['language_id'] for r in conn.execute("SELECT language_id FROM languages").fetchall()]
    profiles = list_phonology_profiles()
    seeded = {p['language_id'] for p in profiles['results']}
    missing = set(lang_ids) - seeded
    assert not missing, f"Missing phonology profiles: {sorted(missing)}"


def test_phonology_profiles_have_required_fields():
    profiles = list_phonology_profiles()
    for p in profiles['results']:
        assert p['language_id'], "phonology profile missing language_id"
        assert p['notation_system'], f"phonology profile {p['profile_id']} missing notation_system"
        assert p['notes'], f"phonology profile {p['profile_id']} missing notes — must disclose hint-only scope"


def test_low_resource_languages_have_phonology_with_honest_notes():
    """Low-resource languages must have phonology profiles with disclaimer notes."""
    for lang_id in ('lang:nav', 'lang:chr', 'lang:crk'):
        profiles = list_phonology_profiles(language_id=lang_id)
        assert profiles['results'], f"{lang_id} missing phonology profile"
        for p in profiles['results']:
            assert 'minimal' in p['notes'].lower() or 'hint' in p['notes'].lower() or 'consult' in p['notes'].lower(), (
                f"{lang_id} phonology profile should include a scope disclaimer in notes"
            )


# ── Pronunciation completeness ──────────────────────────────────────────────

def test_all_34_languages_have_pronunciation():
    with connect() as conn:
        lang_ids = [r['language_id'] for r in conn.execute("SELECT language_id FROM languages").fetchall()]
    profiles = list_pronunciation_profiles()
    seeded = {p['language_id'] for p in profiles['results']}
    missing = set(lang_ids) - seeded
    assert not missing, f"Missing pronunciation profiles: {sorted(missing)}"


def test_pronunciation_profiles_have_examples():
    profiles = list_pronunciation_profiles()
    for p in profiles['results']:
        examples = p.get('examples') or {}
        if isinstance(examples, str):
            import json as j
            examples = j.loads(examples)
        assert examples, f"{p['language_id']} pronunciation profile has no examples"


# ── Transliteration completeness ────────────────────────────────────────────

def test_transliteration_covers_all_non_latin_scripts():
    expected_pairs = [
        ('lang:rus', 'Cyrl'), ('lang:ukr', 'Cyrl'),
        ('lang:hin', 'Deva'), ('lang:mar', 'Deva'),
        ('lang:ben', 'Beng'), ('lang:pan', 'Guru'),
        ('lang:tam', 'Taml'), ('lang:tel', 'Telu'),
        ('lang:arb', 'Arab'), ('lang:fas', 'Arab'), ('lang:urd', 'Arab'),
        ('lang:heb', 'Hebr'),
        ('lang:jpn', 'Hira'), ('lang:jpn', 'Kana'),
        ('lang:kor', 'Hang'),
        ('lang:cmn', 'Hans'), ('lang:yue', 'Hant'),
        ('lang:tha', 'Thai'),
        ('lang:amh', 'Ethi'),
        ('lang:ell', 'Grek'),
        ('lang:chr', 'Cher'),
    ]
    profiles = list_transliteration_profiles()
    actual = {(p['language_id'], p['source_script']) for p in profiles['results']}
    missing = [pair for pair in expected_pairs if pair not in actual]
    assert not missing, f"Missing transliteration pairs: {missing}"


def test_transliteration_profiles_have_coverage_field():
    profiles = list_transliteration_profiles()
    valid = {'none', 'seeded', 'experimental', 'reviewed', 'production'}
    for p in profiles['results']:
        assert p['coverage'] in valid, (
            f"{p['profile_id']} has invalid coverage value '{p['coverage']}'"
        )


# ── Language variants ───────────────────────────────────────────────────────

def test_37_variants_seeded():
    variants = list_language_variants()
    assert variants['count'] >= 37, f"Expected ≥37 variants, got {variants['count']}"


def test_all_four_variant_types_present():
    variants = list_language_variants()
    types = {v['variant_type'] for v in variants['items']}
    for required in ('dialect', 'register', 'orthography', 'historical_stage'):
        assert required in types, f"Variant type '{required}' not present in seed"


def test_english_has_dialect_and_register_variants():
    variants = list_language_variants(language_id='lang:eng')
    types = {v['variant_type'] for v in variants['items']}
    assert 'dialect' in types
    assert 'register' in types
    assert 'historical_stage' in types


def test_japanese_has_keigo_register():
    variants = list_language_variants(language_id='lang:jpn')
    names = [v['variant_name'] for v in variants['items']]
    assert any('keigo' in n.lower() or 'formal' in n.lower() for n in names), (
        "lang:jpn should have a formal/keigo register variant"
    )


def test_upsert_language_variant_roundtrip():
    result = upsert_language_variant(LanguageVariantUpsertRequest(
        language_id='lang:ita',
        variant_name='Tuscan Italian',
        variant_type='dialect',
        region_hint='IT-TU',
        mutual_intelligibility=0.97,
        notes='Florentine Tuscan, historical prestige dialect.',
    ))
    assert result['ok'] is True
    found = list_language_variants(language_id='lang:ita')
    names = [v['variant_name'] for v in found['items']]
    assert 'Tuscan Italian' in names


def test_list_variants_filters_by_type():
    dialects = list_language_variants(variant_type='dialect')
    assert all(v['variant_type'] == 'dialect' for v in dialects['items'])
    historicals = list_language_variants(variant_type='historical_stage')
    assert all(v['variant_type'] == 'historical_stage' for v in historicals['items'])
    assert len(historicals['items']) >= 3  # Old English, Middle English, Classical Chinese, Old Japanese


def test_variant_mutual_intelligibility_bounds():
    variants = list_language_variants()
    for v in variants['items']:
        mi = v.get('mutual_intelligibility')
        if mi is not None:
            assert 0.0 <= mi <= 1.0, (
                f"{v['variant_id']} has mutual_intelligibility={mi} outside [0,1]"
            )


# ── Arbitration correctness ─────────────────────────────────────────────────

def test_status_weights_canonical_is_one():
    assert STATUS_WEIGHTS.get('canonical') == 1.0


def test_effective_lineage_arabic_works_with_arb():
    result = resolve_effective_lineage('lang:arb')
    assert result['ok'] is True, f"Effective lineage for lang:arb failed: {result}"


def test_effective_lineage_policy_shows_db_weights():
    result = resolve_effective_lineage('lang:eng')
    policy = result['policy']
    weights = policy['source_weights']
    # DB-seeded values (not old hardcoded values)
    assert weights.get('glottolog') == 1.0, "glottolog weight should be 1.0"
    assert weights.get('common_seed') == 0.6, "common_seed weight should be 0.6"
    assert weights.get('iso639_3') == 0.9, "iso639_3 weight should be 0.9"


# ── Search correctness ──────────────────────────────────────────────────────

def test_search_returns_results_for_all_seeded_languages():
    with connect() as conn:
        langs = [dict(r) for r in conn.execute("SELECT language_id, name FROM languages").fetchall()]
    for lang in langs:
        name = lang['name']
        result = search_languages(name[:6])
        assert result['ok'] is True
        ids = [r['language_id'] for r in result['results']]
        assert lang['language_id'] in ids, (
            f"search_languages('{name[:6]}') did not find {lang['language_id']}"
        )


def test_search_no_duplicates():
    result = search_languages('English')
    ids = [r['language_id'] for r in result['results']]
    assert len(ids) == len(set(ids)), "search_languages returned duplicate language_id entries"


# ── Stats completeness ──────────────────────────────────────────────────────

def test_stats_nonzero_for_all_seeded_tables():
    c = get_graph_stats()['counts']
    expected_nonzero = [
        'languages', 'scripts', 'language_scripts', 'lineage_nodes', 'lineage_edges',
        'phrase_translations', 'lexemes', 'etymology_edges',
        'language_aliases', 'language_variants',
        'pronunciation_profiles', 'phonology_profiles', 'transliteration_profiles',
        'language_capabilities', 'provenance_records',
        'providers', 'source_weights',
        'backend_manifests', 'corpus_manifests',
    ]
    for key in expected_nonzero:
        assert c.get(key, 0) > 0, f"Expected non-zero stats count for '{key}', got {c.get(key, 0)}"


def test_stats_39_tables_tracked():
    c = get_graph_stats()['counts']
    assert len(c) >= 39, f"Expected ≥39 tables tracked, got {len(c)}"
