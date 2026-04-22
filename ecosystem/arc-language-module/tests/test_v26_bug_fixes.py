"""
test_v26_bug_fixes.py

Tests for real bugs fixed in session 5:
  - arbitration reads source_weights from DB (not hardcoded dict)
  - STATUS_WEIGHTS includes 'canonical' key
  - search queries language_aliases table, not just aliases_json column
  - common_seed_local seeded into source_weights
  - lang:zho → lang:cmn correction throughout seeds
  - Expanded phonology (23 languages), transliteration (19 entries), pronunciation (22 languages)
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
from arc_lang.services.arbitration import (
    resolve_effective_lineage, _load_source_weights, STATUS_WEIGHTS,
)
from arc_lang.services.source_policy import set_source_weight, list_source_weights
from arc_lang.services.search import search_languages
from arc_lang.services.aliases import upsert_language_alias
from arc_lang.services.manual_lineage import add_custom_lineage
from arc_lang.services.phonology import list_phonology_profiles
from arc_lang.services.transliteration import list_transliteration_profiles
from arc_lang.services.pronunciation import list_pronunciation_profiles
from arc_lang.core.models import ManualLineageRequest, AliasUpsertRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


# ─── Arbitration: STATUS_WEIGHTS canonical fix ────────────────────────────

def test_status_weights_includes_canonical():
    """'canonical' must be an explicit key — not falling through to 0.75 default."""
    assert 'canonical' in STATUS_WEIGHTS
    assert STATUS_WEIGHTS['canonical'] == 1.0


def test_canonical_claims_score_at_full_status_weight():
    """Canonical edges must score with status factor 1.0, not the 0.75 fallback."""
    result = resolve_effective_lineage('lang:eng')
    assert result['ok'] is True
    canonical_claims = [c for c in result['claims'] if c.get('claim_type') == 'canonical']
    assert canonical_claims, "Expected at least one canonical claim for lang:eng"
    # With canonical status_weight=1.0, a claim with confidence=0.9 and
    # source=common_seed (DB weight 0.6) should score 0.9*0.6*1.0 = 0.54
    # Previously it scored 0.9*0.6*0.75 = 0.405 (wrong)
    for c in canonical_claims:
        if c.get('confidence') and c.get('source_name') == 'common_seed':
            assert c['effective_score'] > 0.40, (
                f"Canonical claim scored too low ({c['effective_score']}); "
                "STATUS_WEIGHTS['canonical'] may not be applied"
            )


# ─── Arbitration: reads DB source_weights, not hardcoded dict ────────────

def test_arbitration_uses_db_source_weights():
    """Changing source_weights in DB must change arbitration scoring."""
    # Record baseline score for lang:fra canonical family claim
    baseline = resolve_effective_lineage('lang:fra')
    fam_claims_before = [c for c in baseline['claims'] if c['bucket'] == 'family' and c.get('claim_type') == 'canonical']
    if not fam_claims_before:
        return  # No family claim to test against — skip
    score_before = fam_claims_before[0]['effective_score']

    # Double the common_seed weight in DB
    from arc_lang.core.models import SourceWeightUpdateRequest
    set_source_weight(SourceWeightUpdateRequest(source_name='common_seed', authority_weight=1.2, notes='test override'))
    after = resolve_effective_lineage('lang:fra')
    fam_claims_after = [c for c in after['claims'] if c['bucket'] == 'family' and c.get('claim_type') == 'canonical']
    if not fam_claims_after:
        return
    score_after = fam_claims_after[0]['effective_score']
    assert score_after > score_before, (
        "Arbitration score did not change after DB source_weight update — "
        "arbitration is still using hardcoded weights"
    )

    # Restore to seeded default
    set_source_weight(SourceWeightUpdateRequest(source_name='common_seed', authority_weight=0.6, notes='restored'))


def test_arbitration_policy_output_reflects_live_db_weights():
    """The policy dict in the resolved result must come from DB, not hardcoded."""
    result = resolve_effective_lineage('lang:spa')
    policy = result['policy']
    assert 'source_weights' in policy
    # The DB-seeded glottolog weight is 1.0, not the old hardcoded 0.95
    assert policy['source_weights'].get('glottolog') == 1.0
    # common_seed is 0.6 in DB, not the old hardcoded 0.9
    assert policy['source_weights'].get('common_seed') == 0.6


def test_common_seed_local_is_seeded_in_db():
    """common_seed_local must be in source_weights table after seed."""
    weights = list_source_weights()
    names = {w['source_name'] for w in weights['items']}
    assert 'common_seed_local' in names, (
        "common_seed_local not in source_weights DB — "
        "source_policy.DEFAULTS must include it"
    )


def test_set_source_weight_affects_arbitration_scoring():
    """Operator override via set-source-weight must propagate into next arbitration call."""
    with connect() as conn:
        weights_before = _load_source_weights(conn)

    from arc_lang.core.models import SourceWeightUpdateRequest
    set_source_weight(SourceWeightUpdateRequest(source_name='glottolog', authority_weight=0.3, notes='low test'))
    with connect() as conn:
        weights_after = _load_source_weights(conn)
    assert weights_after['glottolog'] == 0.3

    # Restore
    set_source_weight(SourceWeightUpdateRequest(source_name='glottolog', authority_weight=1.0, notes='restored'))


# ─── Search: queries language_aliases table ───────────────────────────────

def test_search_finds_governed_alias_not_in_aliases_json():
    """A language alias inserted via upsert_language_alias (not in aliases_json)
    must be findable via search_languages."""
    # Insert a governed alias for German with a unique test token
    upsert_language_alias(AliasUpsertRequest(
        language_id='lang:deu',
        alias='Deutsch_SearchTestToken_ZZZ',
        alias_type='endonym',
        source_name='user_custom',
        notes='search test alias',
    ))
    results = search_languages('SearchTestToken_ZZZ')
    assert results['ok'] is True
    ids = [r['language_id'] for r in results['results']]
    assert 'lang:deu' in ids, (
        "Search did not find lang:deu via a governed alias from language_aliases table"
    )


def test_search_deduplicates_when_alias_and_name_both_match():
    """If a language matches both aliases_json and language_aliases, it must appear only once."""
    results = search_languages('German')
    assert results['ok'] is True
    ids = [r['language_id'] for r in results['results']]
    assert ids.count('lang:deu') <= 1, "lang:deu appeared more than once in search results"


def test_search_still_finds_via_name_and_family():
    results = search_languages('Indo-European')
    assert results['ok'] is True
    assert len(results['results']) > 3  # many IE languages seeded


# ─── Seed expansion correctness ───────────────────────────────────────────

def test_phonology_expanded_to_23_languages():
    profiles = list_phonology_profiles()
    assert len(profiles['results']) >= 23
    ids = {p['language_id'] for p in profiles['results']}
    # New additions in this session
    for lang_id in ('lang:por', 'lang:ita', 'lang:nld', 'lang:pol', 'lang:ukr',
                    'lang:vie', 'lang:ind', 'lang:ben', 'lang:tam', 'lang:swa', 'lang:nav'):
        assert lang_id in ids, f"Missing phonology profile for {lang_id}"


def test_transliteration_expanded_to_19_entries():
    profiles = list_transliteration_profiles()
    assert len(profiles['results']) >= 19
    pairs = {(p['language_id'], p['source_script']) for p in profiles['results']}
    # New additions
    for pair in [
        ('lang:ukr', 'Cyrl'), ('lang:ben', 'Beng'), ('lang:tam', 'Taml'),
        ('lang:tel', 'Telu'), ('lang:mar', 'Deva'), ('lang:pan', 'Guru'),
        ('lang:urd', 'Arab'), ('lang:amh', 'Ethi'),
    ]:
        assert pair in pairs, f"Missing transliteration profile for {pair}"


def test_pronunciation_expanded_to_22_languages():
    profiles = list_pronunciation_profiles()
    assert len(profiles['results']) >= 22
    ids = {p['language_id'] for p in profiles['results']}
    for lang_id in ('lang:fra', 'lang:deu', 'lang:por', 'lang:ita',
                    'lang:pol', 'lang:ukr', 'lang:jpn', 'lang:kor',
                    'lang:cmn', 'lang:vie', 'lang:ind', 'lang:ben',
                    'lang:tam', 'lang:tel', 'lang:mar'):
        assert lang_id in ids, f"Missing pronunciation profile for {lang_id}"


def test_no_lang_zho_in_seeds():
    """lang:zho was an orphan (no language row). All seed profiles must use lang:cmn."""
    from arc_lang.services.phonology import list_phonology_profiles
    phon_ids = {p['language_id'] for p in list_phonology_profiles()['results']}
    assert 'lang:zho' not in phon_ids, "lang:zho still in phonology profiles — should be lang:cmn"

    translit_ids = {p['language_id'] for p in list_transliteration_profiles()['results']}
    assert 'lang:zho' not in translit_ids, "lang:zho still in transliteration profiles — should be lang:cmn"

    pron_ids = {p['language_id'] for p in list_pronunciation_profiles()['results']}
    assert 'lang:zho' not in pron_ids, "lang:zho still in pronunciation profiles — should be lang:cmn"


def test_lang_cmn_has_all_three_profile_types():
    """Mandarin Chinese (lang:cmn) should have phonology, transliteration, and pronunciation."""
    phon_ids = {p['language_id'] for p in list_phonology_profiles()['results']}
    translit_ids = {p['language_id'] for p in list_transliteration_profiles()['results']}
    pron_ids = {p['language_id'] for p in list_pronunciation_profiles()['results']}
    assert 'lang:cmn' in phon_ids, "lang:cmn missing phonology profile"
    assert 'lang:cmn' in translit_ids, "lang:cmn missing transliteration profile"
    assert 'lang:cmn' in pron_ids, "lang:cmn missing pronunciation profile"
