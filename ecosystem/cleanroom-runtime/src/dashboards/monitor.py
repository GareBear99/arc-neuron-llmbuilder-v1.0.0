from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def render_monitor_panel(info: dict[str, Any], state: dict[str, Any]) -> str:
    world = state.get('world_model', {}) if isinstance(state, dict) else {}
    known_files = world.get('known_files', []) or []
    recent_outputs = world.get('recent_outputs', []) or []
    db_stats = info.get('db_stats', {}) if isinstance(info, dict) else {}
    paths = info.get('paths', {}) if isinstance(info, dict) else {}
    lines = [
        'ARC Lucifer Monitor',
        f"timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"workspace: {paths.get('workspace')}",
        f"db_path: {paths.get('db_path')}",
        f"events: {db_stats.get('event_count', 0)} | db_bytes: {db_stats.get('db_bytes', 0)} | wal_bytes: {db_stats.get('wal_bytes', 0)}",
        f"proposals: {len(state.get('proposals', []))} | receipts: {len(state.get('receipts', []))} | pending: {len(state.get('pending_confirmations', []))}",
        f"benchmarks: {len(state.get('benchmark_runs', []))} | model_runs: {len(state.get('model_runs', []))} | archives: {len(state.get('archive_manifests', []))}",
        f"known_files: {len(known_files)}",
    ]
    if known_files:
        lines.append('files: ' + ', '.join(item.get('path', '?') for item in known_files[:5]))
    if recent_outputs:
        latest = recent_outputs[-1]
        lines.append('latest_output_path: ' + str(latest.get('path')))
    return '\n'.join(lines)
