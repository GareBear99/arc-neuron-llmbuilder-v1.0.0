from __future__ import annotations

from arc_kernel.engine import KernelEngine
from lucifer_runtime.cli import main
from memory_subsystem import MemoryManager
from self_improve import ImprovementAnalyzer


def test_memory_search_ranks_mirrored_memory(tmp_path):
    kernel = KernelEngine(db_path=tmp_path / 'events.sqlite3')
    event = kernel.record_input('user', {
        'text': 'archive policy discussion',
        'memory_title': 'Archive Mirror Policy',
        'memory_summary': 'Mirror archive items early while keeping them live in front memory.',
        'memory_keywords': ['archive', 'mirror', 'front-memory'],
        'memory_importance': 'high',
        'memory_category': 'policy',
    })
    manager = MemoryManager(kernel, tmp_path / 'memory')
    manager.archive_now_but_keep_live(event.event_id, reason='manual_override')

    result = manager.search_memory('archive mirror', limit=5)
    assert result['status'] == 'ok'
    assert result['result_count'] >= 1
    top = result['results'][0]
    assert top['event_id'] == event.event_id
    assert top['status'] == 'live_and_archived'
    assert top['score'] > 0


def test_cli_memory_search_and_status(tmp_path, capsys):
    assert main(['--workspace', str(tmp_path), 'write', 'notes.txt', 'hello world']) == 0
    capsys.readouterr()
    # Mirror one of the created events so status/search have readable archive data.
    kernel = KernelEngine(db_path=tmp_path / '.arc_lucifer' / 'events.sqlite3')
    event = kernel.record_input('user', {
        'text': 'seo memory policy',
        'memory_title': 'SEO Memory Policy',
        'memory_summary': 'Readable stacked memory with title, summary, and keywords.',
        'memory_keywords': ['seo', 'memory', 'archive'],
    })
    kernel.close()
    assert main(['--workspace', str(tmp_path), 'memory', 'archive-now', event.event_id, '--reason', 'manual_override']) == 0
    capsys.readouterr()

    assert main(['--workspace', str(tmp_path), 'memory', 'status']) == 0
    status_out = capsys.readouterr().out
    assert 'records' in status_out
    assert 'live_and_archived' in status_out

    assert main(['--workspace', str(tmp_path), 'memory', 'search', 'seo archive']) == 0
    search_out = capsys.readouterr().out
    assert 'SEO Memory Policy' in search_out
    assert 'result_count' in search_out


def test_analyzer_uses_memory_and_fallback_signals(tmp_path):
    kernel = KernelEngine(db_path=tmp_path / 'events.sqlite3')
    event = kernel.record_input('user', {
        'text': 'memory-rich task',
        'memory_title': 'Retention Plan',
        'memory_summary': 'Retention plan for mirrored archive memories.',
        'memory_keywords': ['retention', 'archive', 'mirror'],
    })
    kernel.record_memory_update('memory-manager', {
        'kind': 'archive_mirrored',
        'target_event_id': event.event_id,
        'title': 'Retention Plan',
        'summary': 'Retention plan for mirrored archive memories.',
        'keywords': ['retention', 'archive', 'mirror'],
        'archive_branch_id': 'archive_branch_main',
    })
    kernel.record_evaluation('resilience', {
        'kind': 'fallback_event',
        'mode': 'deterministic_router',
        'reason': 'model_unavailable',
    })
    kernel.record_evaluation('resilience', {
        'kind': 'fallback_event',
        'mode': 'deterministic_router',
        'reason': 'model_unavailable',
    })
    kernel.record_evaluation('resilience', {
        'kind': 'fallback_event',
        'mode': 'echo_stub',
        'reason': 'stream_error',
    })
    state = kernel.state()
    analysis = ImprovementAnalyzer().analyze(state, tmp_path)
    keys = {target['key'] for target in analysis['targets']}
    assert 'memory_guided_planning' in keys
    assert 'fallback_hotspots' in keys
