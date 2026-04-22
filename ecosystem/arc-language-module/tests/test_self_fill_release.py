from __future__ import annotations

import json
from pathlib import Path

from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.source_policy import seed_source_weights
from arc_lang.services.self_fill_release import run_recurring_self_fill_release, list_self_fill_release_runs, list_self_fill_release_artifacts


def test_recurring_self_fill_release_produces_artifacts(monkeypatch, tmp_path):
    init_db()
    ingest_common_seed()
    seed_source_weights()
    monkeypatch.setenv('ARC_LANG_SIGNING_KEY', 'test-signing-key')
    result = run_recurring_self_fill_release()
    assert result['ok'] is True
    manifest = Path(result['manifest_path'])
    signature = Path(result['signature_path'])
    ledger = Path(result['ledger_path'])
    archive = Path(result['archive_path'])
    assert manifest.exists()
    assert signature.exists()
    assert ledger.exists()
    assert archive.exists()
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    assert payload['signature']['signature_type'] == 'hmac-sha256'
    runs = list_self_fill_release_runs(limit=5)
    assert runs['results']
    artifacts = list_self_fill_release_artifacts(release_run_id=result['release_run_id'])
    kinds = {item['artifact_kind'] for item in artifacts['results']}
    assert {'manifest', 'signature', 'ledger', 'archive'}.issubset(kinds)
