from __future__ import annotations

from pathlib import Path

from arc_lang.core.config import DB_PATH
from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.source_policy import seed_source_weights
from arc_lang.services.self_fill_retention import seed_self_fill_retention_policies, run_scheduled_self_fill_release_cycle, list_self_fill_rollback_index
from arc_lang.services.self_fill_replay import build_self_fill_replay_manifest, compact_self_fill_release, restore_self_fill_snapshot, list_self_fill_replay_runs, list_self_fill_compaction_actions


def test_self_fill_replay_restore_and_compaction(monkeypatch):
    init_db()
    ingest_common_seed()
    seed_source_weights()
    seed_self_fill_retention_policies()
    monkeypatch.setenv('ARC_LANG_SIGNING_KEY', 'test-signing-key')
    scheduled = run_scheduled_self_fill_release_cycle()
    release_run_id = scheduled['release']['release_run_id']
    indexes = list_self_fill_rollback_index(limit=5)
    assert indexes['results']

    replay = build_self_fill_replay_manifest(release_run_id=release_run_id)
    assert replay['ok'] is True
    manifest_path = Path(replay['replay_manifest_path'])
    assert manifest_path.exists()

    compact = compact_self_fill_release(release_run_id=release_run_id)
    assert compact['ok'] is True
    assert Path(compact['compact_bundle_path']).exists()

    before_bytes = DB_PATH.read_bytes()
    restore = restore_self_fill_snapshot(release_run_id=release_run_id)
    assert restore['ok'] is True
    assert Path(restore['restored_snapshot_path']).exists()
    assert DB_PATH.read_bytes() == Path(restore['restored_snapshot_path']).read_bytes()
    assert before_bytes == DB_PATH.read_bytes()

    replay_runs = list_self_fill_replay_runs(limit=10)
    assert replay_runs['results']
    compactions = list_self_fill_compaction_actions(limit=10)
    assert compactions['results']
