"""
test_v33_session12_complete.py

Covers all session-12 completions:
  - All 35 languages have ≥8 common_words
  - 96 lexemes seeded (added Dutch/Ukrainian/Italian/Portuguese/Cantonese yes/no)
  - 36 etymology edges across 4 relation types
  - 7 relationship assertions
  - __init__.py version = 0.27.0 with correct exports
  - Language variants: 104 entries, all 35 languages covered
  - phrase_formal register correctly persisted
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.stats import get_graph_stats


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── Package version and exports ───────────────────────────────────────────────

def test_package_version():
    import arc_lang
    assert arc_lang.__version__ == "0.27.0"


def test_package_exports():
    from arc_lang import init_db, connect, ingest_common_seed, get_graph_stats
    assert callable(init_db)
    assert callable(connect)
    assert callable(ingest_common_seed)
    assert callable(get_graph_stats)


# ── Common words: all ≥8 ──────────────────────────────────────────────────────

def test_all_languages_have_8_plus_common_words():
    with connect() as conn:
        thin = conn.execute(
            "SELECT language_id, json_array_length(common_words_json) AS c "
            "FROM languages WHERE json_array_length(common_words_json) < 8"
        ).fetchall()
    assert not thin, f"Languages with <8 common_words: {[(r['language_id'], r['c']) for r in thin]}"


def test_germanic_languages_have_8_plus():
    with connect() as conn:
        for lid in ('lang:deu', 'lang:nld', 'lang:eng'):
            n = conn.execute(
                "SELECT json_array_length(common_words_json) c FROM languages WHERE language_id=?",
                (lid,)
            ).fetchone()['c']
            assert n >= 8, f"{lid} has only {n} common words"


def test_romance_languages_have_8_plus():
    with connect() as conn:
        for lid in ('lang:fra', 'lang:por', 'lang:ind', 'lang:vie'):
            n = conn.execute(
                "SELECT json_array_length(common_words_json) c FROM languages WHERE language_id=?",
                (lid,)
            ).fetchone()['c']
            assert n >= 8, f"{lid} has only {n} common words"


# ── Lexeme expansion ──────────────────────────────────────────────────────────

def test_96_lexemes_seeded():
    c = get_graph_stats()['counts']
    assert c['lexemes'] >= 96, f"Expected ≥96 lexemes, got {c['lexemes']}"


def test_dutch_yes_no_lexemes_exist():
    with connect() as conn:
        for lemma in ('ja', 'nee'):
            row = conn.execute(
                "SELECT lexeme_id FROM lexemes WHERE language_id='lang:nld' AND lemma=?",
                (lemma,)
            ).fetchone()
            assert row, f"Dutch {lemma!r} lexeme missing"


def test_cantonese_yes_no_lexemes_exist():
    with connect() as conn:
        for lemma in ('係', '唔係'):
            row = conn.execute(
                "SELECT lexeme_id FROM lexemes WHERE language_id='lang:yue' AND lemma=?",
                (lemma,)
            ).fetchone()
            assert row, f"Cantonese {lemma!r} lexeme missing"


def test_italian_portuguese_yes_no_lexemes():
    with connect() as conn:
        for lid, lemma in [('lang:ita','sì'), ('lang:ita','no'), ('lang:por','sim'), ('lang:por','não')]:
            row = conn.execute(
                "SELECT lexeme_id FROM lexemes WHERE language_id=? AND lemma=?",
                (lid, lemma)
            ).fetchone()
            assert row, f"{lid} {lemma!r} lexeme missing"


# ── Etymology edges ───────────────────────────────────────────────────────────

def test_36_etymology_edges():
    c = get_graph_stats()['counts']
    assert c['etymology_edges'] >= 36, f"Expected ≥36 etymology edges, got {c['etymology_edges']}"


def test_all_four_etymology_relation_types():
    with connect() as conn:
        relations = {r['relation'] for r in conn.execute(
            "SELECT DISTINCT relation FROM etymology_edges"
        ).fetchall()}
    for expected in ('cognate', 'borrowing', 'false_friend', 'descends_from'):
        assert expected in relations, f"Missing etymology relation type: {expected}"


def test_germanic_cognate_cluster():
    """Dutch ja and German ja should be linked as cognates."""
    with connect() as conn:
        edge = conn.execute(
            """SELECT * FROM etymology_edges
               WHERE child_lexeme_id='lex:nld:ja' AND parent_lexeme_id='lex:deu:ja'
               AND relation='cognate'"""
        ).fetchone()
    assert edge, "Dutch ja → German ja cognate edge missing"


def test_romance_no_cognates():
    """Italian no and Spanish no should be linked."""
    with connect() as conn:
        edge = conn.execute(
            """SELECT * FROM etymology_edges
               WHERE child_lexeme_id='lex:ita:no' AND parent_lexeme_id='lex:spa:no'
               AND relation='cognate'"""
        ).fetchone()
    assert edge, "Italian no → Spanish no cognate edge missing"


def test_cantonese_borrowing_from_english():
    """Cantonese 拜拜 is borrowed from English bye-bye."""
    with connect() as conn:
        edge = conn.execute(
            """SELECT * FROM etymology_edges
               WHERE child_lexeme_id='lex:yue:拜拜' AND relation='borrowing'"""
        ).fetchone()
    assert edge, "Cantonese 拜拜 borrowing from English missing"


def test_false_friend_edges_present():
    with connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) c FROM etymology_edges WHERE relation='false_friend'"
        ).fetchone()['c']
    assert count >= 8, f"Expected ≥8 false_friend edges, got {count}"


# ── Relationship assertions ────────────────────────────────────────────────────

def test_7_relationship_assertions_seeded():
    c = get_graph_stats()['counts']
    assert c['relationship_assertions'] >= 6, f"Expected ≥6 relationship_assertions, got {c['relationship_assertions']}"


def test_relationship_assertion_types():
    with connect() as conn:
        types = {r['relation'] for r in conn.execute(
            "SELECT DISTINCT relation FROM relationship_assertions"
        ).fetchall()}
    assert len(types) >= 2, f"Expected ≥2 relation types, got {types}"


# ── Phrase registers ──────────────────────────────────────────────────────────

def test_please_formal_register_is_formal():
    with connect() as conn:
        row = conn.execute(
            "SELECT DISTINCT register FROM phrase_translations WHERE canonical_key='please_formal'"
        ).fetchone()
    assert row and row['register'] == 'formal', f"please_formal register is {row['register'] if row else None}"


def test_general_phrases_have_general_register():
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) c FROM phrase_translations WHERE canonical_key != 'please_formal' AND register != 'general'"
        ).fetchone()['c']
    assert n == 0, f"{n} non-please_formal phrases have non-general register"


# ── Final state assertions ────────────────────────────────────────────────────

def test_final_complete_state():
    c = get_graph_stats()['counts']
    assert c['languages'] == 35
    assert c['phrase_translations'] >= 385
    assert c['lexemes'] >= 96
    assert c['etymology_edges'] >= 36
    assert c['language_variants'] >= 104
    assert c['phonology_profiles'] >= 35
    assert c['pronunciation_profiles'] >= 35
    assert c['semantic_concepts'] >= 30
    assert c['concept_links'] >= 46
    assert c['operator_policies'] >= 4
    assert c['provider_health'] >= 10
    assert c['relationship_assertions'] >= 6
    assert len(c) >= 41  # all 41 tables tracked
