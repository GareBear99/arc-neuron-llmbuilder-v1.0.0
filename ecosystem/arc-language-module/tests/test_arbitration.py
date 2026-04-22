from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.manual_lineage import add_custom_lineage
from arc_lang.services.arbitration import resolve_effective_lineage
from arc_lang.core.models import ManualLineageRequest, ReviewDecisionRequest
from arc_lang.services.governance import record_review_decision


def test_effective_lineage_prefers_canonical_seed_by_default():
    init_db()
    ingest_common_seed()
    result = resolve_effective_lineage('lang:spa')
    assert result['ok'] is True
    assert result['effective_truth']['family']['winner']['dst_id'] == 'family:indo_european'


def test_effective_lineage_can_accept_local_override_after_review():
    init_db()
    ingest_common_seed()
    added = add_custom_lineage(ManualLineageRequest(
        src_id='lang:spa',
        dst_id='family:test-family',
        relation='custom_member_of_family',
        confidence=0.99,
        source_name='user_custom',
        status='accepted_local',
        notes='local experimental classification',
    ))
    review = record_review_decision(ReviewDecisionRequest(
        target_type='custom_lineage',
        target_id=added['assertion_id'],
        decision='accepted_local',
        reviewer='tester',
        confidence=0.95,
        notes='accepted for local working graph',
    ))
    assert review['ok'] is True
    result = resolve_effective_lineage('lang:spa')
    assert result['effective_truth']['family']['winner']['dst_id'] == 'family:test-family'


def test_effective_lineage_flags_close_conflict():
    init_db()
    ingest_common_seed()
    add_custom_lineage(ManualLineageRequest(
        src_id='lang:spa',
        dst_id='family:iberian-local',
        relation='custom_member_of_family',
        confidence=0.9,
        source_name='common_seed_local',
        status='accepted_local',
        notes='strong local counterclaim',
    ))
    result = resolve_effective_lineage('lang:spa')
    assert any(c['bucket'] == 'family' for c in result['conflicts'])
