from pathlib import Path
from arc_lang.core.db import init_db, connect
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.importers import import_glottolog_csv, import_iso639_csv, import_cldr_json
from arc_lang.services.search import search_languages
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.lineage import get_lineage


ROOT = Path(__file__).resolve().parents[1]


def setup_module(module):
    init_db()
    ingest_common_seed()
    import_glottolog_csv(ROOT / 'examples' / 'glottolog_sample.csv')
    import_iso639_csv(ROOT / 'examples' / 'iso6393_sample.csv')
    import_cldr_json(ROOT / 'examples' / 'cldr_sample.json')


def test_imported_language_exists():
    with connect() as conn:
        row = conn.execute('SELECT name, iso639_3 FROM languages WHERE language_id = ?', ('lang:nav',)).fetchone()
    assert row['name'] == 'Navajo'
    assert row['iso639_3'] == 'nav'


def test_imported_script_link_exists():
    with connect() as conn:
        row = conn.execute('SELECT 1 FROM language_scripts WHERE language_id = ? AND script_id = ?', ('lang:ron', 'Latn')).fetchone()
    assert row is not None


def test_language_search_finds_imported_alias():
    res = search_languages('Diné')
    assert res['ok'] is True
    assert any(r['language_id'] == 'lang:nav' for r in res['results'])


def test_stats_include_import_runs_and_lineage_nodes():
    stats = get_graph_stats()
    assert stats['counts']['import_runs'] >= 3
    assert stats['counts']['lineage_nodes'] >= 1


def test_imported_lineage_resolves_family_node():
    res = get_lineage('lang:nav')
    assert res['ok'] is True
    assert any(n['node_type'] == 'family' and n['name'] == 'Na-Dene' for n in res['lineage_nodes'])


def test_importers_has_no_duplicate_helper_definitions():
    src = (ROOT / 'src' / 'arc_lang' / 'services' / 'importers.py').read_text(encoding='utf-8')
    assert src.count('def _normalize_aliases(') == 1
    assert src.count('def _normalize_scripts(') == 1
    assert src.count('def _slug(') == 1
    assert src.count('def _record_import_run(') == 1
    assert src.count('def _upsert_provenance(') == 1
    assert src.count('def _ensure_lineage_node(') == 1
    assert src.count('def _ensure_language_row(') == 1
