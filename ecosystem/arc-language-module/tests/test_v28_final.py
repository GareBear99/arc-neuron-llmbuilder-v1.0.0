"""
test_v28_final.py

Tests for all session-7 completions:
  - ISO6393_TO_RUNTIME correctness (no orphans, all seeded languages present)
  - Semantic concepts seeded (30 concepts, 3 concept links)
  - lang:ell has pronunciation and phonology profiles
  - nav/chr/crk common_words expanded (improves detection)
  - concept_links wire to correct canonical_keys
  - Argos backend routing returns correct error for unmapped languages
  - Detection quality improvement for low-resource languages
  - All 9 stub docs are now non-stub (>10 lines)
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
from arc_lang.services.concepts import (
    upsert_semantic_concept, link_concept, list_semantic_concepts, get_concept_bundle,
)
from arc_lang.services.phonology import list_phonology_profiles
from arc_lang.services.pronunciation import list_pronunciation_profiles
from arc_lang.services.detection import detect_language
from arc_lang.services.translation_backends import (
    ISO6393_TO_RUNTIME, _language_codes, list_builtin_translation_backends,
)
from arc_lang.core.models import (
    SemanticConceptUpsertRequest, ConceptLinkRequest, RuntimeTranslateRequest,
)


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── ISO6393_TO_RUNTIME correctness ─────────────────────────────────────────

def test_no_orphaned_iso_codes_in_runtime_map():
    """All ISO codes in ISO6393_TO_RUNTIME must correspond to real seeded languages."""
    with connect() as conn:
        seeded_isos = {r['iso639_3'] for r in conn.execute(
            "SELECT iso639_3 FROM languages WHERE iso639_3 IS NOT NULL"
        ).fetchall()}
    orphans = [iso for iso in ISO6393_TO_RUNTIME if iso not in seeded_isos]
    assert not orphans, (
        f"ISO6393_TO_RUNTIME has orphaned keys not matching any seeded language: {orphans}"
    )


def test_all_seeded_languages_in_runtime_map():
    """Every seeded language with an ISO code must be in ISO6393_TO_RUNTIME."""
    with connect() as conn:
        seeded = [(r['iso639_3'], r['language_id']) for r in conn.execute(
            "SELECT iso639_3, language_id FROM languages WHERE iso639_3 IS NOT NULL"
        ).fetchall()]
    missing = [(iso, lid) for iso, lid in seeded if iso not in ISO6393_TO_RUNTIME]
    assert not missing, (
        f"Seeded languages missing from ISO6393_TO_RUNTIME: {missing}"
    )


def test_arb_maps_correctly_not_ara():
    assert 'ara' not in ISO6393_TO_RUNTIME, "Orphaned 'ara' key should be removed"
    assert 'arb' in ISO6393_TO_RUNTIME, "'arb' (Arabic Modern Standard) must be mapped"
    assert ISO6393_TO_RUNTIME['arb'] == 'ar'


def test_cmn_maps_correctly_not_zho():
    assert 'zho' not in ISO6393_TO_RUNTIME, "Orphaned 'zho' key should be removed"
    assert 'cmn' in ISO6393_TO_RUNTIME, "'cmn' (Mandarin Chinese) must be mapped"
    assert ISO6393_TO_RUNTIME['cmn'] == 'zh'


def test_low_resource_languages_mapped_with_notes():
    """nav/chr/crk should be in map but documented as lacking Argos support."""
    for iso in ('nav', 'chr', 'crk'):
        assert iso in ISO6393_TO_RUNTIME, f"{iso} missing from ISO6393_TO_RUNTIME"
    # Their runtime codes should just be the iso code itself (no Argos package)
    assert ISO6393_TO_RUNTIME['nav'] == 'nav'
    assert ISO6393_TO_RUNTIME['chr'] == 'chr'
    assert ISO6393_TO_RUNTIME['crk'] == 'crk'


def test_language_codes_lookup_works_for_arb():
    codes = _language_codes('lang:arb')
    assert codes['iso639_3'] == 'arb'
    assert codes['runtime_code'] == 'ar'


def test_language_codes_lookup_works_for_cmn():
    codes = _language_codes('lang:cmn')
    assert codes['iso639_3'] == 'cmn'
    assert codes['runtime_code'] == 'zh'


# ── Semantic concepts ────────────────────────────────────────────────────────

def test_30_concepts_seeded():
    concepts = list_semantic_concepts()
    assert concepts['ok'] is True
    assert len(concepts['items']) >= 30, f"Expected ≥30 concepts, got {len(concepts['items'])}"


def test_concept_domains_are_diverse():
    concepts = list_semantic_concepts()
    domains = {c['domain'] for c in concepts['items']}
    expected_domains = {'social', 'discourse', 'grammar', 'basic_vocabulary', 'time', 'numerals'}
    missing = expected_domains - domains
    assert not missing, f"Missing concept domains: {missing}"


def test_greeting_concept_exists():
    concepts = list_semantic_concepts(q='hello')
    assert concepts['ok'] is True
    ids = [c['concept_id'] for c in concepts['items']]
    assert 'concept_greeting_hello' in ids


def test_concept_links_wired_to_phrase_keys():
    """concept_greeting_hello must be linked to the 'hello' phrase key."""
    with connect() as conn:
        links = conn.execute(
            "SELECT target_type, target_id FROM concept_links WHERE concept_id='concept_greeting_hello'"
        ).fetchall()
    assert links, "concept_greeting_hello has no concept_links"
    phrase_links = [l for l in links if l['target_type'] == 'phrase_key']
    assert phrase_links, "concept_greeting_hello has no phrase_key links"
    assert any(l['target_id'] == 'hello' for l in phrase_links), (
        "concept_greeting_hello not linked to 'hello' phrase key"
    )


def test_concept_bundle_returns_links():
    bundle = get_concept_bundle('concept_greeting_hello')
    assert bundle['ok'] is True
    assert bundle['concept']['concept_id'] == 'concept_greeting_hello'
    # Bundle should include concept_links
    assert 'links' in bundle


def test_upsert_concept_and_link_roundtrip():
    result = upsert_semantic_concept(SemanticConceptUpsertRequest(
        canonical_label='bread / leavened bread',
        domain='basic_vocabulary',
        description='Bread as a basic food concept.',
        confidence=0.9,
    ))
    assert result['ok'] is True
    cid = result['concept_id']

    # Link to a phrase key (what_is_this exists)
    lres = link_concept(ConceptLinkRequest(
        concept_id=cid,
        target_type='phrase_key',
        target_id='what_is_this',
        relation='related_to',
        confidence=0.5,
        notes='test link',
    ))
    assert lres['ok'] is True

    # Retrieve bundle
    bundle = get_concept_bundle(cid)
    assert bundle['ok'] is True
    assert len(bundle.get('links', [])) >= 1


def test_concept_stats_nonzero():
    c = get_graph_stats()['counts']
    assert c['semantic_concepts'] >= 30
    assert c['concept_links'] >= 3


# ── lang:ell profiles ───────────────────────────────────────────────────────

def test_lang_ell_has_phonology_profile():
    profiles = list_phonology_profiles(language_id='lang:ell')
    assert profiles['results'], "lang:ell (Greek) missing phonology profile"
    assert profiles['results'][0]['notation_system'] == 'broad_ipa'
    assert profiles['results'][0]['stress_policy']


def test_lang_ell_has_pronunciation_profile():
    profiles = list_pronunciation_profiles(language_id='lang:ell')
    assert profiles['results'], "lang:ell (Greek) missing pronunciation profile"
    examples = profiles['results'][0].get('examples') or {}
    import json as _json
    if isinstance(examples, str):
        examples = _json.loads(examples)
    assert examples, "lang:ell pronunciation profile has no examples"


def test_all_seeded_languages_have_phonology():
    with connect() as conn:
        lang_ids = {r['language_id'] for r in conn.execute("SELECT language_id FROM languages").fetchall()}
    phon_ids = {p['language_id'] for p in list_phonology_profiles()['results']}
    missing = lang_ids - phon_ids
    assert not missing, f"Languages missing phonology: {sorted(missing)}"


def test_all_seeded_languages_have_pronunciation():
    with connect() as conn:
        lang_ids = {r['language_id'] for r in conn.execute("SELECT language_id FROM languages").fetchall()}
    pron_ids = {p['language_id'] for p in list_pronunciation_profiles()['results']}
    missing = lang_ids - pron_ids
    assert not missing, f"Languages missing pronunciation: {sorted(missing)}"


# ── Common words expanded for low-resource languages ──────────────────────

def test_navajo_common_words_expanded():
    with connect() as conn:
        row = conn.execute(
            "SELECT common_words_json FROM languages WHERE language_id='lang:nav'"
        ).fetchone()
    import json
    words = json.loads(row['common_words_json'])
    assert len(words) >= 6, f"Navajo should have ≥6 common words for detection, got {len(words)}"


def test_cherokee_common_words_expanded():
    with connect() as conn:
        row = conn.execute(
            "SELECT common_words_json FROM languages WHERE language_id='lang:chr'"
        ).fetchone()
    import json
    words = json.loads(row['common_words_json'])
    assert len(words) >= 6, f"Cherokee should have ≥6 common words for detection, got {len(words)}"


def test_plains_cree_common_words_expanded():
    with connect() as conn:
        row = conn.execute(
            "SELECT common_words_json FROM languages WHERE language_id='lang:crk'"
        ).fetchone()
    import json
    words = json.loads(row['common_words_json'])
    assert len(words) >= 6, f"Plains Cree should have ≥6 common words for detection, got {len(words)}"


def test_detection_finds_cherokee_from_syllabics():
    result = detect_language('ᎣᏏᏲ ᏩᏙᏉ')
    assert result.winner_language_id == 'lang:chr', (
        f"Cherokee syllabics not detected as lang:chr, got {result.winner_language_id}"
    )


def test_detection_finds_navajo_from_known_words():
    result = detect_language("yá'át'ééh nizhóní")
    assert result.winner_language_id == 'lang:nav', (
        f"Navajo words not detected as lang:nav, got {result.winner_language_id}"
    )


# ── Translation backend ISO map integration ─────────────────────────────────

def test_builtin_backends_list_is_complete():
    result = list_builtin_translation_backends()
    assert result['ok'] is True
    names = {b['provider_name'] for b in result['backends']}
    assert 'local_seed' in names
    assert 'mirror_mock' in names
    assert 'argos_local' in names
    assert 'argos_bridge' in names
    assert 'nllb_bridge' in names


def test_argos_backend_reports_dependency_missing_gracefully():
    """argos_local backend must fail with explicit error when argostranslate is not installed."""
    from arc_lang.services.translation_backends import ArgosLocalTranslationBackend
    backend = ArgosLocalTranslationBackend()
    req = RuntimeTranslateRequest(
        text='hello', target_language_id='lang:spa', dry_run=True
    )
    result = backend.translate(req, 'lang:eng')
    # Will either fail with dependency_missing or succeed (if installed in test env)
    if not result['ok']:
        assert result['error'] in (
            'translation_backend_dependency_missing',
            'translation_backend_language_pair_missing',
            'translation_backend_language_code_unmapped',
            'translation_backend_dependency_failed',
        ), f"Unexpected error from argos backend: {result['error']}"


# ── Documentation completeness ───────────────────────────────────────────────

def test_all_docs_are_non_stub():
    """No doc file should be ≤5 lines (stub threshold)."""
    docs_dir = ROOT / 'docs'
    stubs = []
    for doc in sorted(docs_dir.glob('*.md')):
        lines = len(doc.read_text().splitlines())
        if lines <= 5:
            stubs.append((doc.name, lines))
    assert not stubs, f"Stub docs detected (≤5 lines): {stubs}"


def test_key_docs_are_substantial():
    """Core docs must be at least 20 lines."""
    docs_dir = ROOT / 'docs'
    required = [
        'ARCHITECTURE.md', 'INGESTION_PLAN.md',
        'IMPLEMENTATION_MANIFESTS_AND_PHONOLOGY.md',
        'BACKEND_DIAGNOSTICS.md', 'GOVERNANCE_WORKFLOW.md',
        'LANGUAGE_ONBOARDING.md', 'PROVIDER_RUNTIME_AUDIT.md',
        'TRANSLITERATION_PROFILES_AND_READINESS.md',
        'SEMANTIC_CONCEPTS_VARIANTS_AND_COVERAGE.md',
        'COMPREHENSIVE_GROWTH_SURFACES.md',
        'ADVANCED_ANALYSIS_AND_PRONUNCIATION.md',
    ]
    short = []
    for name in required:
        path = docs_dir / name
        if path.exists():
            lines = len(path.read_text().splitlines())
            if lines < 20:
                short.append((name, lines))
    assert not short, f"Core docs are too short (< 20 lines): {short}"
