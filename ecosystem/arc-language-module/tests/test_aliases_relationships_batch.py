import json
from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.core.models import AliasUpsertRequest, RelationshipAssertionRequest, BatchImportRequest, BatchExportRequest, SourceWeightUpdateRequest
from arc_lang.services.aliases import upsert_language_alias, list_language_aliases
from arc_lang.services.relationships import add_relationship_assertion, list_relationship_assertions
from arc_lang.services.batch_io import batch_import, batch_export, list_batch_runs
from arc_lang.services.source_policy import list_source_weights, set_source_weight


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_alias_upsert_and_list():
    res = upsert_language_alias(AliasUpsertRequest(language_id='lang:spa', alias='Español', alias_type='endonym', script_id='Latn'))
    assert res['ok'] is True
    listing = list_language_aliases(language_id='lang:spa', q='Espa')
    assert listing['count'] >= 1


def test_relationship_assertion_roundtrip():
    with connect() as conn:
        src = conn.execute("SELECT lexeme_id FROM lexemes WHERE language_id='lang:ita' AND lemma='ciao'").fetchone()['lexeme_id']
        dst = conn.execute("SELECT lexeme_id FROM lexemes WHERE language_id='lang:spa' LIMIT 1").fetchone()['lexeme_id']
    res = add_relationship_assertion(RelationshipAssertionRequest(src_lexeme_id=src, dst_lexeme_id=dst, relation='borrowing'))
    assert res['ok'] is True
    listing = list_relationship_assertions(lexeme_id=src)
    assert listing['count'] >= 1


def test_batch_import_export_and_runs(tmp_path):
    payload = {'items': [{'language_id': 'lang:gswx', 'name': 'TestLang', 'family': 'TestFam', 'scripts': ['Latn']}]}
    inp = tmp_path/'subs.json'
    inp.write_text(json.dumps(payload), encoding='utf-8')
    res = batch_import(BatchImportRequest(input_path=str(inp), object_type='language_submissions', dry_run=False))
    assert res['ok'] is True
    outp = tmp_path/'langs.json'
    ex = batch_export(BatchExportRequest(output_path=str(outp), object_type='languages'))
    assert ex['ok'] is True and outp.exists()
    runs = list_batch_runs()
    assert runs['count'] >= 2


def test_source_weights_present_and_mutable():
    listing = list_source_weights()
    assert listing['count'] >= 3
    upd = set_source_weight(SourceWeightUpdateRequest(source_name='user_custom', authority_weight=0.7))
    assert upd['ok'] is True
