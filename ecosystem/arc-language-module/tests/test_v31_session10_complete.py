"""
test_v31_session10_complete.py

Tests for all session-10 completions:
  - operator_policies seeded via ingest_common_seed
  - provider_health seeded (10 snapshots, local=healthy, bridges=offline)
  - relationship_assertions seeded (6 cross-lexeme edges)
  - All 25 list_* functions have docstrings
  - pyproject.toml has classifiers and keywords
  - Runtime orchestration correct with seeded health records
  - Personaplex offline by default; can be overridden for test scenarios
"""
from __future__ import annotations
import sys, ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.policy import get_policy_snapshot
from arc_lang.services.provider_registry import list_providers, set_provider_health, provider_is_usable
from arc_lang.services.relationships import list_relationship_assertions


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── operator_policies seeded ──────────────────────────────────────────────

def test_operator_policies_seeded_by_ingest():
    c = get_graph_stats()['counts']
    assert c['operator_policies'] >= 4, (
        f"Expected ≥4 operator_policies, got {c['operator_policies']}"
    )


def test_all_default_policies_present():
    snap = get_policy_snapshot()
    keys = set(snap['policy_values'].keys())
    required = {'runtime_default_dry_run', 'allow_external_providers',
                'allow_mutation_actions', 'allow_live_speech'}
    missing = required - keys
    assert not missing, f"Missing default policies: {missing}"


def test_default_policy_values_are_safe():
    snap = get_policy_snapshot()
    vals = snap['policy_values']
    # Safe defaults: dry_run on, live speech off, mutation off
    assert vals['runtime_default_dry_run'] == 'true'
    assert vals['allow_live_speech'] == 'false'
    assert vals['allow_mutation_actions'] == 'false'


# ── provider_health seeded ────────────────────────────────────────────────

def test_10_provider_health_records_seeded():
    c = get_graph_stats()['counts']
    assert c['provider_health'] >= 10, (
        f"Expected ≥10 provider_health records, got {c['provider_health']}"
    )


def test_local_providers_seeded_healthy():
    for provider in ('local_seed', 'local_detect', 'local_graph', 'local_map', 'mirror_mock'):
        result = provider_is_usable(provider)
        assert result['usable'] is True, (
            f"{provider} should be usable after seed; got: {result}"
        )


def test_bridge_stubs_seeded_offline():
    for provider in ('argos_bridge', 'nllb_bridge', 'personaplex'):
        result = provider_is_usable(provider)
        assert result['usable'] is False, (
            f"{provider} should be offline (boundary stub); got: {result}"
        )
        assert result.get('reason') == 'provider_offline', (
            f"{provider} offline reason should be 'provider_offline'; got: {result.get('reason')}"
        )


def test_argos_local_seeded_degraded():
    """argos_local is seeded as 'degraded' — honest: installed but no models."""
    with connect() as conn:
        row = conn.execute(
            "SELECT status FROM provider_health WHERE provider_name='argos_local' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row['status'] == 'degraded'


def test_provider_health_overridable():
    """Operators can override seed health with set_provider_health."""
    set_provider_health('argos_local', 'healthy', latency_ms=50, error_rate=0.01,
                        notes='test: argos installed and models present')
    result = provider_is_usable('argos_local')
    assert result['usable'] is True
    # Restore
    set_provider_health('argos_local', 'degraded',
                        notes='Optional — healthy only if argostranslate installed with models')


# ── relationship_assertions seeded ───────────────────────────────────────

def test_6_relationship_assertions_seeded():
    c = get_graph_stats()['counts']
    assert c['relationship_assertions'] >= 6, (
        f"Expected ≥6 relationship_assertions, got {c['relationship_assertions']}"
    )


def test_seeded_relationship_types():
    with connect() as conn:
        relations = {r['relation'] for r in conn.execute(
            "SELECT DISTINCT relation FROM relationship_assertions"
        ).fetchall()}
    assert 'cognate' in relations
    assert 'borrowing' in relations
    assert 'false_friend' in relations


def test_romance_gratitude_cognate_seeded():
    """gracias (spa) → grazie (ita) should be seeded as cognate."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM relationship_assertions WHERE src_lexeme_id='lex:spa:gracias' AND relation='cognate'"
        ).fetchone()
    assert row, "Expected spa:gracias → ita:grazie cognate assertion"
    assert row['dst_lexeme_id'] == 'lex:ita:grazie'
    assert row['confidence'] >= 0.9


def test_list_relationship_assertions_works():
    result = list_relationship_assertions()
    assert result['ok'] is True
    assert len(result['items']) >= 6
    # All items have required fields
    for item in result['items']:
        assert 'src_lexeme_id' in item
        assert 'dst_lexeme_id' in item
        assert 'relation' in item
        assert 'confidence' in item


def test_list_relationship_assertions_filter_by_relation():
    result = list_relationship_assertions(relation='false_friend')
    assert result['ok'] is True
    assert all(r['relation'] == 'false_friend' for r in result['items'])
    assert len(result['items']) >= 2  # spa:gracias→fra:merci, arb→fas, arb→heb


def test_list_relationship_assertions_filter_by_lexeme():
    result = list_relationship_assertions(lexeme_id='lex:spa:gracias')
    assert result['ok'] is True
    ids = [r['src_lexeme_id'] + r['dst_lexeme_id'] for r in result['items']]
    assert any('lex:spa:gracias' in s for s in ids)


# ── list_* docstrings ─────────────────────────────────────────────────────

def test_all_list_functions_have_docstrings():
    """Every list_* function in every service module must have a docstring."""
    services_dir = ROOT / 'src' / 'arc_lang' / 'services'
    missing_docs = []
    for pyfile in sorted(services_dir.glob('*.py')):
        if pyfile.name.startswith('__'):
            continue
        src = pyfile.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('list_'):
                has_doc = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)
                )
                if not has_doc:
                    missing_docs.append(f"{pyfile.name}::{node.name}")
    assert not missing_docs, f"list_* functions without docstrings: {missing_docs}"


# ── pyproject.toml completeness ───────────────────────────────────────────

def test_pyproject_has_classifiers():
    content = (ROOT / 'pyproject.toml').read_text()
    assert 'classifiers' in content
    assert 'Development Status' in content
    assert 'Topic :: Text Processing :: Linguistic' in content
    assert 'Programming Language :: Python :: 3.12' in content


def test_pyproject_has_keywords():
    content = (ROOT / 'pyproject.toml').read_text()
    assert 'keywords' in content
    assert 'linguistics' in content
    assert 'low-resource' in content


def test_pyproject_has_license():
    content = (ROOT / 'pyproject.toml').read_text()
    assert 'license' in content
    assert 'MIT' in content


def test_pyproject_dev_deps_include_pytest_cov():
    content = (ROOT / 'pyproject.toml').read_text()
    assert 'pytest-cov' in content


# ── Full state after session 10 ───────────────────────────────────────────

def test_session10_final_state():
    c = get_graph_stats()['counts']
    # Everything seeded in session 10
    assert c['operator_policies'] >= 4
    assert c['provider_health'] >= 10
    assert c['relationship_assertions'] >= 6
    # Nothing broke from prior sessions
    assert c['languages'] == 35
    assert c['phrase_translations'] >= 350
    assert c['lexemes'] >= 82
    assert c['etymology_edges'] >= 9
    assert c['semantic_concepts'] >= 30
    assert c['concept_links'] >= 46
    assert c['phonology_profiles'] >= 35
    assert c['pronunciation_profiles'] >= 35
    assert c['transliteration_profiles'] >= 21
    assert c['language_variants'] >= 100
    assert c['source_weights'] >= 7
    assert c['providers'] >= 10
    assert len(c) >= 41
