from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fixnet.models import utcnow_iso


class ContinuityShell:
    def __init__(self, runtime_root: str | Path, *, runtime_name: str = 'lucifer-runtime') -> None:
        self.runtime_root = Path(runtime_root)
        self.dir = self.runtime_root / '.arc_lucifer' / 'continuity'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / 'state.json'
        self.boot_path = self.dir / 'boot_receipts.json'
        if not self.state_path.exists():
            self.state_path.write_text(json.dumps({
                'runtime_id': str(uuid4()),
                'runtime_name': runtime_name,
                'boot_count': 0,
                'last_mode': 'uninitialized',
                'last_boot_at': None,
                'last_heartbeat_at': None,
                'last_reason': '',
            }, indent=2, sort_keys=True), encoding='utf-8')
        if not self.boot_path.exists():
            self.boot_path.write_text(json.dumps({'receipts': []}, indent=2, sort_keys=True), encoding='utf-8')

    def _load_state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding='utf-8'))

    def _save_state(self, data: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def _load_boots(self) -> dict[str, Any]:
        return json.loads(self.boot_path.read_text(encoding='utf-8'))

    def _save_boots(self, data: dict[str, Any]) -> None:
        self.boot_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def boot(self, *, active_directive_count: int, primary_available: bool, fallback_available: bool = True, notes: str = '') -> dict[str, Any]:
        state = self._load_state()
        now = utcnow_iso()
        if primary_available:
            mode = 'primary'
            reason = 'primary cognition core available'
        elif fallback_available:
            mode = 'fallback'
            reason = 'primary unavailable; fallback continuity engaged'
        else:
            mode = 'degraded'
            reason = 'primary and fallback unavailable'
        state['boot_count'] = int(state.get('boot_count', 0)) + 1
        state['last_mode'] = mode
        state['last_boot_at'] = now
        state['last_heartbeat_at'] = now
        state['last_reason'] = reason
        self._save_state(state)
        receipt = {
            'receipt_id': str(uuid4()),
            'runtime_id': state.get('runtime_id'),
            'runtime_name': state.get('runtime_name'),
            'boot_index': state['boot_count'],
            'booted_at': now,
            'mode': mode,
            'reason': reason,
            'notes': notes,
            'active_directive_count': active_directive_count,
            'primary_available': primary_available,
            'fallback_available': fallback_available,
        }
        boots = self._load_boots()
        boots.setdefault('receipts', []).append(receipt)
        self._save_boots(boots)
        return receipt

    def heartbeat(self, *, mode: str | None = None, notes: str = '') -> dict[str, Any]:
        state = self._load_state()
        now = utcnow_iso()
        if mode:
            state['last_mode'] = mode
        state['last_heartbeat_at'] = now
        if notes:
            state['last_reason'] = notes
        self._save_state(state)
        return {
            'runtime_id': state.get('runtime_id'),
            'runtime_name': state.get('runtime_name'),
            'mode': state.get('last_mode'),
            'heartbeat_at': now,
            'notes': notes,
        }

    def status(self) -> dict[str, Any]:
        state = self._load_state()
        boots = self._load_boots().get('receipts', [])
        return {
            **state,
            'recent_boot_receipts': boots[-10:],
        }

    def watchdog(self, *, stale_after_seconds: int = 300) -> dict[str, Any]:
        state = self._load_state()
        last_heartbeat = state.get('last_heartbeat_at')
        if not last_heartbeat:
            return {'healthy': False, 'mode': state.get('last_mode', 'uninitialized'), 'reason': 'no heartbeat recorded', 'stale_after_seconds': stale_after_seconds}
        from datetime import datetime, timezone
        last = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
        age = (datetime.now(timezone.utc) - last).total_seconds()
        return {
            'healthy': age <= stale_after_seconds,
            'mode': state.get('last_mode', 'unknown'),
            'last_heartbeat_at': last_heartbeat,
            'age_seconds': round(age, 3),
            'stale_after_seconds': stale_after_seconds,
        }
