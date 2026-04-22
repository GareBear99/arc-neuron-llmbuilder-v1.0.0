from pathlib import Path
from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.manual_lineage import add_custom_lineage, list_custom_lineage
from arc_lang.services.onboarding import submit_language, list_language_submissions, approve_language_submission, export_language_submission_template, import_language_submission_json
from arc_lang.core.models import ManualLineageRequest, LanguageSubmissionRequest
from arc_lang.services.lineage import get_lineage

ROOT = Path(__file__).resolve().parents[1]


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_submit_and_approve_language_inline():
    res = submit_language(LanguageSubmissionRequest(
        language_id='lang:moh', name='Mohawk', iso639_3='moh', family='Iroquoian', branch='Northern Iroquoian',
        aliases=["Kanien'kéha"], common_words=['nia:wen'], scripts=['Latn'], notes='test submission'
    ))
    assert res['ok'] is True
    approve = approve_language_submission(res['submission_id'])
    assert approve['ok'] is True
    with connect() as conn:
        row = conn.execute('SELECT name, iso639_3 FROM languages WHERE language_id = ?', ('lang:moh',)).fetchone()
        script = conn.execute('SELECT 1 FROM language_scripts WHERE language_id = ? AND script_id = ?', ('lang:moh', 'Latn')).fetchone()
    assert row['name'] == 'Mohawk'
    assert script is not None


def test_custom_lineage_is_separate_and_visible():
    res = add_custom_lineage(ManualLineageRequest(src_id='lang:moh', dst_id='family:iroquoian', relation='custom_member_of_family', notes='researcher note'))
    assert res['ok'] is True
    listing = list_custom_lineage(src_id='lang:moh')
    assert any(r['relation'] == 'custom_member_of_family' for r in listing['results'])
    lineage = get_lineage('lang:moh')
    assert any(r['relation'] == 'custom_member_of_family' for r in lineage['custom_assertions'])


def test_export_and_import_template_json(tmp_path):
    out = tmp_path / 'tmp_submission.json'
    export = export_language_submission_template(out)
    assert export['ok'] is True
    imported = import_language_submission_json(ROOT / 'examples' / 'language_submission_example.json')
    assert imported['ok'] is True
    all_subs = list_language_submissions(status='submitted')
    assert any(r['language_id'] == 'lang:moh' for r in all_subs['results'])
