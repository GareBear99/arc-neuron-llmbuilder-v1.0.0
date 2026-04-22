
import json
from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.core.models import SemanticConceptUpsertRequest, ConceptLinkRequest, LanguageVariantUpsertRequest, ConflictReviewExportRequest, CoverageReportRequest, AliasUpsertRequest, ManualLineageRequest
from arc_lang.services.concepts import upsert_semantic_concept, link_concept, list_semantic_concepts, get_concept_bundle
from arc_lang.services.variants import upsert_language_variant, list_language_variants
from arc_lang.services.conflict_review import export_conflict_review_bundle, list_conflict_review_exports
from arc_lang.services.coverage import build_coverage_report, list_coverage_reports
from arc_lang.services.aliases import upsert_language_alias
from arc_lang.services.manual_lineage import add_custom_lineage
from arc_lang.services.governance import record_review_decision
from arc_lang.core.models import ReviewDecisionRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_semantic_concept_bundle_roundtrip():
    c = upsert_semantic_concept(SemanticConceptUpsertRequest(canonical_label='greeting', domain='speech_act'))
    assert c['ok'] is True
    with connect() as conn:
        lex = conn.execute("SELECT lexeme_id FROM lexemes WHERE language_id='lang:spa' AND lemma='hola'").fetchone()['lexeme_id']
    l = link_concept(ConceptLinkRequest(concept_id=c['concept_id'], target_type='lexeme', target_id=lex))
    assert l['ok'] is True
    listing = list_semantic_concepts(domain='speech_act')
    assert listing['count'] >= 1
    bundle = get_concept_bundle(c['concept_id'])
    assert bundle['count'] >= 1


def test_language_variants_roundtrip():
    res = upsert_language_variant(LanguageVariantUpsertRequest(language_id='lang:eng', variant_name='Scottish English', variant_type='dialect', region_hint='Scotland', status='reviewed', mutual_intelligibility=0.92))
    assert res['ok'] is True
    listing = list_language_variants(language_id='lang:eng', variant_type='dialect')
    assert listing['count'] >= 1


def test_conflict_review_export_and_listing(tmp_path):
    added = add_custom_lineage(ManualLineageRequest(src_id='lang:spa', dst_id='family:germanic', relation='custom_member_of_family', confidence=0.72, notes='intentional conflict'))
    record_review_decision(ReviewDecisionRequest(target_type='custom_lineage', target_id=added['assertion_id'], decision='disputed'))
    out = tmp_path/'conflicts.json'
    res = export_conflict_review_bundle(ConflictReviewExportRequest(output_path=str(out), language_ids=['lang:spa']))
    assert res['ok'] is True and out.exists()
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['summary']['languages_considered'] == 1
    hist = list_conflict_review_exports()
    assert hist['count'] >= 1


def test_coverage_report_export(tmp_path):
    upsert_language_alias(AliasUpsertRequest(language_id='lang:spa', alias='Español', alias_type='endonym'))
    out = tmp_path/'coverage.json'
    res = build_coverage_report(CoverageReportRequest(output_path=str(out), language_ids=['lang:spa','lang:eng']))
    assert res['ok'] is True and out.exists()
    payload = json.loads(out.read_text(encoding='utf-8'))
    assert payload['summary']['languages'] == 2
    reports = list_coverage_reports()
    assert reports['count'] >= 1
