from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.onboarding import submit_language, list_language_submissions
from arc_lang.services.manual_lineage import add_custom_lineage, list_custom_lineage
from arc_lang.services.governance import record_review_decision, list_review_decisions, set_language_capability, get_language_readiness
from arc_lang.core.models import LanguageSubmissionRequest, ManualLineageRequest, ReviewDecisionRequest, CapabilityUpdateRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_review_submission_accepts_locally():
    submitted = submit_language(LanguageSubmissionRequest(
        language_id='lang:tst', name='Test Language', family='Test Family', scripts=['Latn'], notes='governance test'
    ))
    review = record_review_decision(ReviewDecisionRequest(
        target_type='language_submission',
        target_id=submitted['submission_id'],
        decision='accepted_local',
        notes='accepted in local graph',
    ))
    assert review['ok'] is True
    subs = list_language_submissions(status='accepted_local')
    assert any(r['submission_id'] == submitted['submission_id'] for r in subs['results'])


def test_review_custom_lineage_marks_disputed():
    assertion = add_custom_lineage(ManualLineageRequest(
        src_id='lang:tst', dst_id='family:test_family', relation='custom_member_of_family', notes='tentative hypothesis'
    ))
    review = record_review_decision(ReviewDecisionRequest(
        target_type='custom_lineage',
        target_id=assertion['assertion_id'],
        decision='disputed',
        notes='conflicts with second source',
    ))
    assert review['ok'] is True
    listing = list_custom_lineage(status='disputed')
    assert any(r['assertion_id'] == assertion['assertion_id'] for r in listing['results'])


def test_capability_readiness_summary():
    set_language_capability(CapabilityUpdateRequest(language_id='lang:tst', capability_name='detection', maturity='reviewed', confidence=0.82))
    set_language_capability(CapabilityUpdateRequest(language_id='lang:tst', capability_name='lineage', maturity='production', confidence=0.9))
    ready = get_language_readiness('lang:tst')
    assert ready['ok'] is True
    assert ready['overall_maturity'] == 'production'
    assert any(c['capability_name'] == 'detection' for c in ready['capabilities'])


def test_review_records_listable():
    reviews = list_review_decisions(target_type='language_submission')
    assert reviews['ok'] is True
    assert len(reviews['results']) >= 1
