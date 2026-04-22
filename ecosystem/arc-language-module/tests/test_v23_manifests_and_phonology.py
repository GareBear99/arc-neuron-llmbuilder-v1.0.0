from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.phonology import list_phonology_profiles, phonology_hint
from arc_lang.services.manifests import list_backend_manifests, list_corpus_manifests
from arc_lang.services.implementation_matrix import build_implementation_matrix, list_implementation_matrix_reports
from arc_lang.services.stats import get_graph_stats


def test_phonology_seeded_and_hint_available(tmp_path):
    init_db()
    ingest_common_seed()
    profiles = list_phonology_profiles('lang:spa')
    assert profiles['ok'] is True
    assert len(profiles['results']) >= 1
    hint = phonology_hint('hola', 'lang:spa')
    assert hint['ok'] is True
    assert hint['broad_ipa']


def test_backend_and_corpus_manifests_seeded():
    init_db()
    ingest_common_seed()
    backends = list_backend_manifests()
    corpora = list_corpus_manifests()
    assert backends['ok'] is True and len(backends['results']) >= 3
    assert corpora['ok'] is True and any(r['acquisition_status'] == 'external_required' for r in corpora['results'])


def test_implementation_matrix_report_records(tmp_path):
    init_db()
    ingest_common_seed()
    output = tmp_path / 'matrix.json'
    report = build_implementation_matrix(str(output))
    assert report['ok'] is True
    assert output.exists()
    stats = get_graph_stats()['counts']
    assert stats['implementation_matrix_reports'] >= 1
    listed = list_implementation_matrix_reports()
    assert listed['ok'] is True and len(listed['results']) >= 1
