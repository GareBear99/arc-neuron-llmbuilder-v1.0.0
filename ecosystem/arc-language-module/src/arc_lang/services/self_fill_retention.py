from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from arc_lang.core.config import ROOT
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow
from arc_lang.services.self_fill_release import run_recurring_self_fill_release

REPORT_DIR = ROOT / 'docs'
ROLLBACK_DIR = ROOT / 'artifacts' / 'rollback_index'
for d in (REPORT_DIR, ROLLBACK_DIR):
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_POLICIES: list[dict[str, Any]] = [
    {
        'policy_name': 'hourly_hot_window',
        'schedule_kind': 'hourly',
        'retention_class': 'hot',
        'keep_days': 7,
        'keep_count': 48,
        'compact_after_days': 2,
        'notes': 'Keep the most recent governed growth waves immediately replayable.',
    },
    {
        'policy_name': 'daily_warm_window',
        'schedule_kind': 'daily',
        'retention_class': 'warm',
        'keep_days': 60,
        'keep_count': 90,
        'compact_after_days': 14,
        'notes': 'Keep accepted daily language growth waves for operator review and replay.',
    },
    {
        'policy_name': 'monthly_cold_archive',
        'schedule_kind': 'monthly',
        'retention_class': 'cold',
        'keep_days': 3650,
        'keep_count': 240,
        'compact_after_days': 90,
        'notes': 'Long-horizon historical archive; eligible for cold compaction only.',
    },
]


def seed_self_fill_retention_policies() -> dict[str, Any]:
    now = utcnow()
    created = 0
    with connect() as conn:
        for item in DEFAULT_POLICIES:
            exists = conn.execute(
                'SELECT policy_id FROM self_fill_retention_policies WHERE policy_name = ?',
                (item['policy_name'],),
            ).fetchone()
            if exists:
                conn.execute(
                    'UPDATE self_fill_retention_policies SET schedule_kind = ?, retention_class = ?, keep_days = ?, keep_count = ?, compact_after_days = ?, enabled = 1, notes = ?, updated_at = ? WHERE policy_name = ?',
                    (item['schedule_kind'], item['retention_class'], item['keep_days'], item['keep_count'], item['compact_after_days'], item['notes'], now, item['policy_name']),
                )
            else:
                conn.execute(
                    'INSERT INTO self_fill_retention_policies (policy_id, policy_name, schedule_kind, retention_class, keep_days, keep_count, compact_after_days, enabled, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        f'sfrp_{uuid.uuid4().hex[:12]}',
                        item['policy_name'],
                        item['schedule_kind'],
                        item['retention_class'],
                        item['keep_days'],
                        item['keep_count'],
                        item['compact_after_days'],
                        1,
                        item['notes'],
                        now,
                        now,
                    ),
                )
                created += 1
        conn.commit()
    return {'ok': True, 'created_count': created, 'policy_count': len(DEFAULT_POLICIES)}


def list_self_fill_retention_policies(limit: int = 50) -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_retention_policies WHERE enabled = 1 ORDER BY schedule_kind, policy_name LIMIT ?', (limit,)).fetchall()]
    return {'ok': True, 'results': rows}


def _load_release_run(release_run_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute('SELECT * FROM self_fill_release_runs WHERE release_run_id = ?', (release_run_id,)).fetchone()
    if not row:
        raise ValueError(f'Unknown release_run_id: {release_run_id}')
    data = dict(row)
    data['summary'] = json.loads(data.pop('summary_json') or '{}')
    return data


def _choose_retention_class(summary: dict[str, Any]) -> str:
    promoted = int(summary.get('promoted_count') or 0)
    skipped = int(summary.get('skipped_count') or 0)
    if promoted >= 10:
        return 'hot'
    if promoted >= 1:
        return 'warm'
    if skipped > 0:
        return 'cold'
    return 'cold'


def _replay_priority(retention_class: str, summary: dict[str, Any]) -> int:
    base = {'hot': 100, 'warm': 60, 'cold': 20}.get(retention_class, 10)
    return base + min(int(summary.get('promoted_count') or 0), 25)


def _write_rollback_index(release_run: dict[str, Any], retention_class: str) -> Path:
    summary = release_run['summary']
    payload = {
        'rollback_id': f'sfri_{uuid.uuid4().hex[:12]}',
        'release_run_id': release_run['release_run_id'],
        'retention_class': retention_class,
        'replay_priority': _replay_priority(retention_class, summary),
        'manifest_path': release_run['manifest_path'],
        'archive_path': release_run['archive_path'],
        'ledger_path': release_run['ledger_path'],
        'manifest_sha256': summary.get('manifest_sha256', ''),
        'snapshot_path': release_run.get('snapshot_path', ''),
        'created_at': utcnow(),
    }
    path = ROLLBACK_DIR / f"{release_run['release_run_id']}.rollback_index.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return path


def apply_self_fill_retention_policy(release_run_id: str, policy_name: str | None = None) -> dict[str, Any]:
    release_run = _load_release_run(release_run_id)
    retention_class = _choose_retention_class(release_run['summary'])
    with connect() as conn:
        if policy_name:
            policy = conn.execute('SELECT * FROM self_fill_retention_policies WHERE policy_name = ? AND enabled = 1', (policy_name,)).fetchone()
        else:
            policy = conn.execute('SELECT * FROM self_fill_retention_policies WHERE retention_class = ? AND enabled = 1 ORDER BY keep_days ASC LIMIT 1', (retention_class,)).fetchone()
        if not policy:
            raise ValueError(f'No enabled retention policy found for class={retention_class!r}')
        policy = dict(policy)

        rollback_path = _write_rollback_index(release_run, retention_class)
        rollback_payload = json.loads(rollback_path.read_text(encoding='utf-8'))

        conn.execute(
            'INSERT OR REPLACE INTO self_fill_rollback_index (rollback_id, release_run_id, retention_class, replay_priority, manifest_path, archive_path, ledger_path, manifest_sha256, index_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                rollback_payload['rollback_id'],
                release_run_id,
                retention_class,
                rollback_payload['replay_priority'],
                rollback_payload['manifest_path'],
                rollback_payload['archive_path'],
                rollback_payload['ledger_path'],
                rollback_payload['manifest_sha256'],
                str(rollback_path),
                rollback_payload['created_at'],
            ),
        )

        details = {
            'keep_days': policy['keep_days'],
            'keep_count': policy['keep_count'],
            'compact_after_days': policy['compact_after_days'],
            'rollback_index_path': str(rollback_path),
            'replay_priority': rollback_payload['replay_priority'],
        }
        conn.execute(
            'INSERT INTO self_fill_retention_actions (action_id, release_run_id, policy_id, retention_class, action_kind, action_status, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                f'sfra_{uuid.uuid4().hex[:12]}',
                release_run_id,
                policy['policy_id'],
                retention_class,
                'classify_and_index',
                'applied',
                json.dumps(details, ensure_ascii=False, sort_keys=True),
                utcnow(),
            ),
        )
        conn.commit()

    return {
        'ok': True,
        'release_run_id': release_run_id,
        'retention_class': retention_class,
        'policy_name': policy['policy_name'],
        'rollback_index_path': str(rollback_path),
        'replay_priority': rollback_payload['replay_priority'],
    }


def run_scheduled_self_fill_release_cycle(*, schedule_kind: str = 'daily', min_score: float = 0.35, reviewer: str = 'self_fill_release_pipeline', signing_key: str | None = None) -> dict[str, Any]:
    seed_self_fill_retention_policies()
    release = run_recurring_self_fill_release(mode=f'scheduled_{schedule_kind}_pipeline', min_score=min_score, reviewer=reviewer, signing_key=signing_key)
    retention = apply_self_fill_retention_policy(release['release_run_id'])
    report = {
        'ok': True,
        'schedule_kind': schedule_kind,
        'release': release,
        'retention': retention,
    }
    report_path = REPORT_DIR / 'self_fill_scheduled_release_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def list_self_fill_retention_actions(limit: int = 100) -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_retention_actions ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['details'] = json.loads(row.pop('details_json') or '{}')
    return {'ok': True, 'results': rows}


def list_self_fill_rollback_index(limit: int = 100) -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_rollback_index ORDER BY replay_priority DESC, created_at DESC LIMIT ?', (limit,)).fetchall()]
    return {'ok': True, 'results': rows}
