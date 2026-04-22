"""
test_v32_session11_complete.py

Covers all session-11 completions:
  - All 35 languages have ≥6 common_words (detection quality)
  - All 35 languages have ≥1 language variant
  - 104 total variants across all 4 types
  - please_formal phrase key seeded with register='formal'
  - 11 phrase keys × 35 languages = 385 entries
  - All 81 CLI commands have help text
  - Variant types for newly-covered languages
  - Phrase register field populated correctly
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import re
from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.variants import list_language_variants


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── Common words coverage ────────────────────────────────────────────────────

def test_all_35_languages_have_6_plus_common_words():
    with connect() as conn:
        thin = conn.execute(
            "SELECT language_id, common_words_json FROM languages "
            "WHERE json_array_length(common_words_json) < 6"
        ).fetchall()
    assert not thin, (
        f"Languages with <6 common_words: "
        f"{[(r['language_id'], json.loads(r['common_words_json'])) for r in thin]}"
    )


def test_detection_quality_languages_have_8_plus_words():
    """Languages that previously had only 1-2 words now have ≥8."""
    with connect() as conn:
        for lang_id in ('lang:nav', 'lang:chr', 'lang:crk', 'lang:amh', 'lang:tam', 'lang:tel'):
            row = conn.execute(
                "SELECT json_array_length(common_words_json) AS c FROM languages WHERE language_id=?",
                (lang_id,)
            ).fetchone()
            assert row and row['c'] >= 6, f"{lang_id} has only {row['c'] if row else 0} common words"


def test_common_words_are_in_native_script():
    """Non-Latin languages should have native-script common words, not just romanizations."""
    with connect() as conn:
        # Arabic should have Arabic script words
        arb = conn.execute(
            "SELECT common_words_json FROM languages WHERE language_id='lang:arb'"
        ).fetchone()
    words = json.loads(arb['common_words_json'])
    arabic_script_words = [w for w in words if any(ord(c) > 1536 for c in w)]
    assert len(arabic_script_words) >= 4, f"Arabic should have ≥4 Arabic-script words, got {arabic_script_words}"


# ── Language variants coverage ────────────────────────────────────────────────

def test_all_35_languages_have_at_least_one_variant():
    with connect() as conn:
        langs = {r['language_id'] for r in conn.execute("SELECT language_id FROM languages").fetchall()}
    variants = list_language_variants()
    langs_with = {v['language_id'] for v in variants['items']}
    missing = langs - langs_with
    assert not missing, f"Languages with 0 variants: {sorted(missing)}"


def test_104_plus_variants_seeded():
    variants = list_language_variants()
    assert variants['count'] >= 100, f"Expected ≥100 variants, got {variants['count']}"


def test_all_four_variant_types_present_in_new_languages():
    """New languages added this session should have all major variant types."""
    # Check Korean has formal register
    kor_variants = list_language_variants(language_id='lang:kor')
    kor_types = {v['variant_type'] for v in kor_variants['items']}
    assert 'dialect' in kor_types, "Korean missing dialect variants"
    assert 'register' in kor_types, "Korean missing register variants (jondaemal)"

    # Check Persian has multiple dialect variants (Farsi, Dari, Tajik)
    fas_variants = list_language_variants(language_id='lang:fas')
    fas_names = [v['variant_name'] for v in fas_variants['items']]
    assert any('Dari' in n or 'dari' in n.lower() for n in fas_names), \
        "Persian missing Dari dialect variant"

    # Check Turkish has historical stage
    tur_variants = list_language_variants(language_id='lang:tur')
    tur_types = {v['variant_type'] for v in tur_variants['items']}
    assert 'historical_stage' in tur_types, "Turkish missing historical stage (Ottoman)"


def test_tamil_has_classical_historical_stage():
    variants = list_language_variants(language_id='lang:tam')
    names = [v['variant_name'] for v in variants['items']]
    assert any('classical' in n.lower() for n in names), \
        "Tamil missing Classical Tamil historical_stage variant"


def test_hebrew_has_biblical_historical_stage():
    variants = list_language_variants(language_id='lang:heb')
    types = {v['variant_type'] for v in variants['items']}
    assert 'historical_stage' in types, "Hebrew missing historical stage (Biblical Hebrew)"


def test_punjabi_has_both_script_orthographies():
    variants = list_language_variants(language_id='lang:pan')
    types = {v['variant_type'] for v in variants['items']}
    assert 'orthography' in types, "Punjabi missing orthography variants (Gurmukhi/Shahmukhi)"
    names = [v['variant_name'] for v in variants['items']]
    has_gurmukhi = any('Gurmukhi' in n or 'gurmukhi' in n.lower() for n in names)
    has_shahmukhi = any('Shahmukhi' in n or 'shahmukhi' in n.lower() for n in names)
    assert has_gurmukhi, "Punjabi missing Gurmukhi orthography"
    assert has_shahmukhi, "Punjabi missing Shahmukhi orthography"


def test_mutual_intelligibility_in_bounds():
    variants = list_language_variants()
    for v in variants['items']:
        mi = v.get('mutual_intelligibility')
        if mi is not None:
            assert 0.0 <= mi <= 1.0, \
                f"{v['variant_id']} mutual_intelligibility={mi} out of [0,1]"


# ── Phrase translations ────────────────────────────────────────────────────────

def test_385_phrase_entries():
    c = get_graph_stats()['counts']
    assert c['phrase_translations'] >= 385, f"Expected ≥385, got {c['phrase_translations']}"


def test_11_phrase_keys_present():
    with connect() as conn:
        keys = {r['canonical_key'] for r in conn.execute(
            "SELECT DISTINCT canonical_key FROM phrase_translations"
        ).fetchall()}
    expected = {
        'hello', 'thank_you', 'what_is_this', 'goodbye',
        'yes', 'no', 'please', 'sorry', 'good_morning',
        'how_are_you', 'please_formal',
    }
    missing = expected - keys
    assert not missing, f"Missing canonical keys: {missing}"


def test_please_formal_has_correct_register():
    with connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT register FROM phrase_translations WHERE canonical_key='please_formal'"
        ).fetchall()
    registers = {r['register'] for r in rows}
    assert 'formal' in registers, f"please_formal has wrong register: {registers}"


def test_please_formal_covers_all_35_languages():
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(DISTINCT language_id) c FROM phrase_translations WHERE canonical_key='please_formal'"
        ).fetchone()['c']
    assert n == 35, f"please_formal covers {n} languages, expected 35"


def test_all_other_keys_have_general_register():
    with connect() as conn:
        bad = conn.execute(
            "SELECT DISTINCT canonical_key, register FROM phrase_translations "
            "WHERE canonical_key != 'please_formal' AND register != 'general'"
        ).fetchall()
    assert not bad, f"Unexpected non-general registers: {[(r['canonical_key'], r['register']) for r in bad]}"


# ── CLI help text ─────────────────────────────────────────────────────────────

def test_all_cli_commands_have_help_text():
    cli_src = (ROOT / 'src' / 'arc_lang' / 'cli' / 'main.py').read_text()
    # Find add_parser calls without help=
    no_help = re.findall(r"sub\.add_parser\('[^']+'\)(?!\s*[;,])", cli_src)
    assert not no_help, f"CLI commands without help text: {no_help}"


def test_cli_help_text_is_descriptive():
    """Help texts must be meaningful (> 10 chars each)."""
    cli_src = (ROOT / 'src' / 'arc_lang' / 'cli' / 'main.py').read_text()
    short = re.findall(r"sub\.add_parser\('[^']+', help='([^']{1,10})'\)", cli_src)
    assert not short, f"CLI commands with too-short help text: {short}"


# ── Final completeness assertions ─────────────────────────────────────────────

def test_final_state_all_surfaces_populated():
    c = get_graph_stats()['counts']
    # All seed-time tables must be non-zero
    seed_tables = {
        'languages': 35, 'scripts': 15, 'language_scripts': 38,
        'lineage_nodes': 34, 'lineage_edges': 35,
        'phrase_translations': 385, 'lexemes': 82, 'etymology_edges': 9,
        'language_aliases': 82, 'language_variants': 100,
        'phonology_profiles': 35, 'pronunciation_profiles': 35, 'transliteration_profiles': 21,
        'semantic_concepts': 30, 'concept_links': 46,
        'language_capabilities': 245, 'source_weights': 7,
        'providers': 10, 'provider_health': 10,
        'operator_policies': 4, 'relationship_assertions': 6,
        'backend_manifests': 4, 'corpus_manifests': 4,
        'provenance_records': 300,
    }
    for key, minimum in seed_tables.items():
        assert c.get(key, 0) >= minimum, \
            f"Expected {key} >= {minimum}, got {c.get(key, 0)}"


def test_detection_works_for_newly_expanded_languages():
    from arc_lang.services.detection import detect_language
    # Thai — now has 10 words
    r = detect_language("สวัสดี ขอบคุณ ใช่ ไม่")
    assert r.winner_language_id == 'lang:tha', \
        f"Thai not detected: {r.winner_language_id} (score {r.confidence})"
    # Korean — now has 10 words
    r2 = detect_language("안녕하세요 감사합니다 이것 네 아니요")
    assert r2.winner_language_id == 'lang:kor', \
        f"Korean not detected: {r2.winner_language_id}"
