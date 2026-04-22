from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from arc_kernel.engine import KernelEngine
from memory_subsystem import MemoryManager, RetentionConfig


def test_archive_now_mirrors_but_keeps_live_until_schedule(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / 'events.db')
    created = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    event = kernel.record_input('user', {'text': 'important architecture note'})
    event.created_at = created
    manager = MemoryManager(kernel, tmp_path / 'memory', RetentionConfig(hot_days=30, warm_days=180))

    result = manager.archive_now_but_keep_live(event.event_id, reason='manual_override')

    assert result['status'] == 'ok'
    state = kernel.state()
    assert any(update.get('kind') == 'archive_mirrored' and update.get('target_event_id') == event.event_id for update in state.memory_updates)
    # Before scheduled archive date the record remains live, so consolidate should not retire it.
    consolidation = manager.consolidate(now=datetime.now(timezone.utc))
    assert consolidation.archived_count == 0


def test_archive_sync_and_retirement_recorded(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / 'events.db')
    created_dt = datetime.now(timezone.utc) - timedelta(days=10)
    scheduled_dt = datetime.now(timezone.utc) + timedelta(days=5)
    event = kernel.record_input('user', {'text': 'sync me', 'scheduled_archive_at': scheduled_dt.isoformat()})
    event.created_at = created_dt.isoformat()
    manager = MemoryManager(kernel, tmp_path / 'memory', RetentionConfig(hot_days=30, warm_days=180))

    manager.archive_now_but_keep_live(event.event_id)
    sync_result = manager.sync_live_mirrors(event_id=event.event_id)
    assert sync_result['sync_count'] == 1

    # After the scheduled date the record should retire from front memory.
    retire_result = manager.consolidate(now=scheduled_dt + timedelta(days=1))
    assert retire_result.archived_count >= 1
    state = kernel.state()
    assert any(update.get('kind') == 'archive_retired' and update.get('target_event_id') == event.event_id for update in state.memory_updates)


def test_warm_index_contains_readable_header_fields(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / 'events.db')
    created_dt = datetime.now(timezone.utc) - timedelta(days=60)
    event = kernel.record_input('user', {'text': 'Readable memory summary for SEO-like stacking'})
    event.created_at = created_dt.isoformat()
    manager = MemoryManager(kernel, tmp_path / 'memory', RetentionConfig(hot_days=30, warm_days=180))

    manager.consolidate(now=datetime.now(timezone.utc))
    warm_index = (tmp_path / 'memory' / 'warm' / 'warm_index.json').read_text(encoding='utf-8')
    assert 'title' in warm_index
    assert 'summary' in warm_index
    assert 'keywords' in warm_index
