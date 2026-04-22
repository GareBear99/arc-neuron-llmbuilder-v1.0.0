from __future__ import annotations

from pathlib import Path

from arc_lang.core.db import connect, init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.self_fill_sources import (
    list_self_fill_conflicts,
    list_self_fill_import_runs,
    run_approved_source_import_bootstrap,
    stage_iso_fixture_candidates,
)


def test_approved_source_bootstrap_records_runs(tmp_path: Path):
    init_db()
    ingest_common_seed()
    result = run_approved_source_import_bootstrap()
    assert result['ok'] is True
    runs = list_self_fill_import_runs(limit=10)
    assert len(runs['results']) >= 3


def test_iso_importer_stages_candidates(tmp_path: Path):
    init_db()
    ingest_common_seed()
    result = stage_iso_fixture_candidates(Path('examples/iso6393_sample.csv'))
    assert result['ok'] is True
    assert result['candidates_staged'] >= 1
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM self_fill_candidates WHERE source_name = 'iso639_fixture'").fetchone()['c']
    assert count >= 1
    conflicts = list_self_fill_conflicts(limit=20)
    assert conflicts['ok'] is True
