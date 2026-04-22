from __future__ import annotations

from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.self_fill import scan_self_fill_gaps
from arc_lang.services.self_fill_sources import stage_iso_fixture_candidates, stage_glottolog_fixture_candidates
from arc_lang.services.self_fill_arbitration import arbitrate_self_fill_candidates, promote_arbitrated_self_fill_winners
from arc_lang.services.source_policy import set_source_weight
from arc_lang.core.models import SourceWeightUpdateRequest
from arc_lang.core.config import ROOT


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_arbitration_runs_and_writes_receipt():
    scan_self_fill_gaps(stage_candidates=True)
    result = arbitrate_self_fill_candidates(min_score=0.25)
    assert result['ok'] is True
    assert result['summary']['group_count'] > 0
    with connect() as conn:
        row = conn.execute('SELECT 1 FROM self_fill_arbitration_runs WHERE arbitration_run_id = ?', (result['arbitration_run_id'],)).fetchone()
        assert row is not None


def test_source_weight_changes_winner_pool():
    init_db(); ingest_common_seed()
    examples = ROOT / 'examples'
    stage_iso_fixture_candidates(examples / 'iso6393_sample.csv', source_name='iso639_3')
    stage_glottolog_fixture_candidates(examples / 'glottolog_sample.csv', source_name='glottolog')
    high = arbitrate_self_fill_candidates(language_id='lang:nav', min_score=0.0)
    high_scores = {d['winning_score'] for d in high['decisions']}
    set_source_weight(SourceWeightUpdateRequest(source_name='glottolog', authority_weight=0.1, notes='test low'))
    low = arbitrate_self_fill_candidates(language_id='lang:nav', min_score=0.0)
    low_scores = {d['winning_score'] for d in low['decisions']}
    assert high_scores != low_scores


def test_promote_arbitrated_self_fill_promotes_some_candidates():
    init_db(); ingest_common_seed()
    scan_self_fill_gaps(stage_candidates=True)
    result = promote_arbitrated_self_fill_winners(min_score=0.25)
    assert result['ok'] is True
    assert result['promoted_count'] > 0
