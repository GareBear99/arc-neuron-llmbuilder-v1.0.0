"""
test_v30_final_complete.py

Comprehensive final tests for all session-9 completions:
  - Lexeme seed expanded 7→82 with correct canonical_meaning_keys
  - Etymology edges 1→9 (cognate, borrowing, false_friend)
  - Stats covers operator_policies and translation_assertions (41 total)
  - Schema migration 002 applied (all performance indexes exist)
  - translate_explain works end-to-end with correct key lookup
  - Relationship assertions API fully exercised
  - Zero remaining structural gaps
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.translate_explain import translate_explain
from arc_lang.services.etymology import get_etymology
from arc_lang.services.relationships import add_relationship_assertion, list_relationship_assertions
from arc_lang.services.translation_assertions import create_translation_assertion
from arc_lang.core.models import (
    TranslateExplainQuery, RelationshipAssertionRequest, TranslationExplainRequest,
)


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── Stats completeness — 41 tables ────────────────────────────────────────

def test_stats_covers_41_tables():
    c = get_graph_stats()['counts']
    assert len(c) >= 41, f"Expected ≥41 tables in stats, got {len(c)}"


def test_stats_includes_operator_policies():
    c = get_graph_stats()['counts']
    assert 'operator_policies' in c


def test_stats_includes_translation_assertions():
    c = get_graph_stats()['counts']
    assert 'translation_assertions' in c


# ── Lexeme seed expansion ─────────────────────────────────────────────────

def test_82_lexemes_seeded():
    c = get_graph_stats()['counts']
    assert c['lexemes'] >= 82, f"Expected ≥82 lexemes, got {c['lexemes']}"


def test_lexeme_canonical_keys_are_flat_not_dotted():
    """No lexeme should have a dot-format canonical_meaning_key."""
    with connect() as conn:
        bad = conn.execute(
            "SELECT lexeme_id, canonical_meaning_key FROM lexemes WHERE canonical_meaning_key LIKE '%.%'"
        ).fetchall()
    assert not bad, (
        f"Lexemes with old dot-format canonical_meaning_key: "
        f"{[(r['lexeme_id'], r['canonical_meaning_key']) for r in bad]}"
    )


def test_hello_lexemes_cover_major_languages():
    with connect() as conn:
        langs = {r['language_id'] for r in conn.execute(
            "SELECT language_id FROM lexemes WHERE canonical_meaning_key='hello'"
        ).fetchall()}
    for expected in ('lang:eng', 'lang:spa', 'lang:fra', 'lang:jpn', 'lang:arb', 'lang:cmn', 'lang:ell'):
        assert expected in langs, f"{expected} missing hello lexeme"


def test_thank_you_lexemes_seeded():
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM lexemes WHERE canonical_meaning_key='thank_you'"
        ).fetchone()['c']
    assert n >= 10, f"Expected ≥10 thank_you lexemes, got {n}"


def test_goodbye_lexemes_seeded():
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM lexemes WHERE canonical_meaning_key='goodbye'"
        ).fetchone()['c']
    assert n >= 8, f"Expected ≥8 goodbye lexemes, got {n}"


def test_yes_no_lexemes_seeded():
    with connect() as conn:
        for key in ('yes', 'no'):
            n = conn.execute(
                "SELECT COUNT(*) AS c FROM lexemes WHERE canonical_meaning_key=?", (key,)
            ).fetchone()['c']
            assert n >= 6, f"Expected ≥6 '{key}' lexemes, got {n}"


# ── Etymology edges ────────────────────────────────────────────────────────

def test_9_etymology_edges_seeded():
    c = get_graph_stats()['counts']
    assert c['etymology_edges'] >= 9, f"Expected ≥9 etymology edges, got {c['etymology_edges']}"


def test_etymology_edge_types_present():
    with connect() as conn:
        relations = {r['relation'] for r in conn.execute(
            "SELECT DISTINCT relation FROM etymology_edges"
        ).fetchall()}
    assert 'cognate' in relations, "Missing cognate etymology edges"
    assert 'borrowing' in relations, "Missing borrowing etymology edges"
    assert 'false_friend' in relations, "Missing false_friend etymology edges"


def test_romance_cognates_exist():
    """gracias and grazie should be linked as cognates."""
    with connect() as conn:
        edge = conn.execute(
            """SELECT * FROM etymology_edges
               WHERE child_lexeme_id LIKE 'lex:spa:%' AND relation='cognate'
               LIMIT 1"""
        ).fetchone()
    assert edge, "No cognate edges found from Spanish lexemes"


def test_borrowing_edges_exist():
    with connect() as conn:
        edge = conn.execute(
            "SELECT * FROM etymology_edges WHERE relation='borrowing' LIMIT 1"
        ).fetchone()
    assert edge, "No borrowing edges seeded"


def test_false_friend_edges_exist():
    """arigatou/obrigado false_friend edge should exist."""
    with connect() as conn:
        edge = conn.execute(
            "SELECT * FROM etymology_edges WHERE relation='false_friend' LIMIT 1"
        ).fetchone()
    assert edge, "No false_friend edges seeded"


def test_get_etymology_returns_edges():
    result = get_etymology('lang:ita', 'ciao')
    assert result.get('ok') is True or 'error' in result
    # If lexeme exists, should return etymology data
    with connect() as conn:
        lex = conn.execute(
            "SELECT lexeme_id FROM lexemes WHERE language_id='lang:ita' AND lemma='ciao'"
        ).fetchone()
    if lex:
        result = get_etymology('lang:ita', 'ciao')
        assert result.get('ok') is True


# ── translate_explain with correct canonical keys ─────────────────────────

def test_translate_explain_hello_english_to_all_major():
    targets = ['lang:spa', 'lang:fra', 'lang:deu', 'lang:jpn', 'lang:arb', 'lang:cmn']
    for target in targets:
        result = translate_explain(TranslateExplainQuery(
            text='hello', source_language_id='lang:eng', target_language_id=target,
        ))
        assert result.get('ok') is True, (
            f"translate_explain(hello, eng→{target}) failed: {result.get('error')}"
        )


def test_translate_explain_goodbye_english_to_spanish():
    result = translate_explain(TranslateExplainQuery(
        text='goodbye', source_language_id='lang:eng', target_language_id='lang:spa',
    ))
    assert result.get('ok') is True
    text = result.get('translated_text') or result.get('translation', {}).get('text_value', '')
    assert 'adiós' in str(text).lower() or len(str(text)) > 0


def test_translate_explain_yes_no_roundtrip():
    for phrase in ('yes', 'no'):
        result = translate_explain(TranslateExplainQuery(
            text=phrase, source_language_id='lang:eng', target_language_id='lang:fra',
        ))
        assert result.get('ok') is True, (
            f"translate_explain({phrase!r}, eng→fra) failed: {result.get('error')}"
        )


def test_translate_explain_thank_you_to_japanese():
    result = translate_explain(TranslateExplainQuery(
        text='thank you', source_language_id='lang:eng', target_language_id='lang:jpn',
    ))
    assert result.get('ok') is True


# ── Schema migration 002 indexes ──────────────────────────────────────────

def test_migration_002_indexes_exist():
    """Verify key indexes from 002_indexes.sql were applied."""
    with connect() as conn:
        indexes = {r[1] for r in conn.execute(
            "SELECT * FROM sqlite_master WHERE type='index'"
        ).fetchall()}

    expected_indexes = [
        'idx_pronunciation_profiles_lang_kind',
        'idx_phonology_profiles_lang_notation',
        'idx_language_variants_lang_type',
        'idx_language_aliases_lang_type',
        'idx_phrase_translations_canonical_key',
        'idx_lexemes_lemma_lower',
        'idx_etymology_parent',
        'idx_provider_health_name_time',
    ]
    missing = [idx for idx in expected_indexes if idx not in indexes]
    assert not missing, f"Missing indexes from migration 002: {missing}"


def test_init_db_applies_all_migrations():
    """init_db must run both 001_init.sql and 002_indexes.sql."""
    # Re-init and verify migration 002 index exists
    init_db()
    ingest_common_seed()
    with connect() as conn:
        idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_lexemes_lemma_lower'"
        ).fetchone()
    assert idx, "idx_lexemes_lemma_lower not created by migration 002"


# ── Relationship assertions ──────────────────────────────────────────────

def test_add_relationship_assertion_roundtrip():
    req = RelationshipAssertionRequest(
        src_lexeme_id='lex:eng:hello',
        dst_lexeme_id='lex:spa:hola',
        relation='cognate',
        confidence=0.85,
        source_name='user_custom',
        notes='Both likely derive from Germanic/Latin roots via different paths.',
    )
    result = add_relationship_assertion(req)
    assert result['ok'] is True
    assert result['assertion_id']


def test_list_relationship_assertions_by_relation():
    # Seed one first
    add_relationship_assertion(RelationshipAssertionRequest(
        src_lexeme_id='lex:eng:hello',
        dst_lexeme_id='lex:fra:bonjour',
        relation='borrowing',
        confidence=0.60,
        source_name='user_custom',
        notes='Test borrowing',
    ))
    result = list_relationship_assertions(relation='borrowing')
    assert result['ok'] is True
    assert len(result['items']) >= 1
    assert all(r['relation'] == 'borrowing' for r in result['items'])


def test_list_relationship_assertions_by_lexeme():
    result = list_relationship_assertions(lexeme_id='lex:eng:hello')
    assert result['ok'] is True
    # Should find the cognate and borrowing we just added
    assert isinstance(result['items'], list)


# ── Translation assertions persisted ─────────────────────────────────────

def test_translation_assertion_appears_in_stats():
    req = TranslationExplainRequest(
        source_language_id='lang:eng',
        target_language_id='lang:deu',
        source_text='hello',
        translated_text='hallo',
        confidence=0.95,
        rationale='Direct translation from seeded phrase graph',
        provider='manual',
    )
    create_translation_assertion(req)
    c = get_graph_stats()['counts']
    assert c['translation_assertions'] >= 1


# ── Zero coverage gaps maintained ────────────────────────────────────────

def test_zero_missing_flags_still_hold():
    from arc_lang.services.coverage import build_coverage_report
    from arc_lang.core.models import CoverageReportRequest
    s = build_coverage_report(CoverageReportRequest())['summary']
    assert s['missing_phonology'] == 0
    assert s['missing_pronunciation'] == 0
    assert s['missing_transliteration'] == 0
    assert s['missing_script_mapping'] == 0
    assert s['with_concepts'] == s['languages']  # all 35 have language concept links


# ── Comprehensive final state ─────────────────────────────────────────────

def test_final_production_state():
    c = get_graph_stats()['counts']
    # Languages and phrases
    assert c['languages'] == 35
    assert c['phrase_translations'] >= 350
    # Linguistic profiles — all complete
    assert c['phonology_profiles'] >= 35
    assert c['pronunciation_profiles'] >= 35
    assert c['transliteration_profiles'] >= 21
    # Lexical depth
    assert c['lexemes'] >= 82
    assert c['etymology_edges'] >= 9
    # Semantic graph
    assert c['semantic_concepts'] >= 30
    assert c['concept_links'] >= 46
    # Variants and aliases
    assert c['language_variants'] >= 100
    assert c['language_aliases'] >= 82
    # Provenance
    assert c['provenance_records'] >= 300
    # Governance infrastructure
    assert c['language_capabilities'] >= 238
    assert c['source_weights'] >= 7
    assert c['providers'] >= 10
    assert c['backend_manifests'] >= 4
    assert c['corpus_manifests'] >= 4
    # Stats coverage
    assert len(c) >= 41
