from __future__ import annotations

from pathlib import Path

from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.source_policy import seed_source_weights
from arc_lang.services.self_fill_retention import (
    seed_self_fill_retention_policies,
    run_scheduled_self_fill_release_cycle,
    list_self_fill_retention_policies,
    list_self_fill_retention_actions,
    list_self_fill_rollback_index,
)


def test_scheduled_self_fill_release_cycle_creates_retention_and_rollback(monkeypatch):
    init_db()
    ingest_common_seed()
    seed_source_weights()
    seed_self_fill_retention_policies()
    monkeypatch.setenv('ARC_LANG_SIGNING_KEY', 'test-signing-key')
    result = run_scheduled_self_fill_release_cycle()
    assert result['ok'] is True
    retention = result['retention']
    assert retention['retention_class'] in {'hot', 'warm', 'cold'}
    rollback = Path(retention['rollback_index_path'])
    assert rollback.exists()
    policies = list_self_fill_retention_policies(limit=10)
    assert len(policies['results']) >= 3
    actions = list_self_fill_retention_actions(limit=10)
    assert actions['results']
    indexes = list_self_fill_rollback_index(limit=10)
    assert indexes['results']
