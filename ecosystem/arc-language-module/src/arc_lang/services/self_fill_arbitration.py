from __future__ import annotations

import json
import uuid
from collections import defaultdict
from typing import Iterable

from arc_lang.core.db import connect
from arc_lang.core.models import SourceWeightUpdateRequest, utcnow
from arc_lang.services.self_fill import promote_self_fill_candidate
from arc_lang.services.source_policy import set_source_weight

STATUS_WEIGHTS = {
    'staged': 0.92,
    'reviewed': 1.0,
    'promoted': 1.0,
}

SURFACE_WEIGHTS = {
    'alias': 0.98,
    'capability': 0.95,
    'transliteration_profile': 0.96,
    'pronunciation_profile': 0.94,
    'phonology_profile': 0.93,
}


def _load_source_weights(conn) -> dict[str, float]:
    rows = conn.execute('SELECT source_name, authority_weight FROM source_weights').fetchall()
    return {r['source_name']: float(r['authority_weight']) for r in rows}


def _payload(candidate: dict) -> dict:
    return json.loads(candidate.get('payload_json') or '{}')


def _group_key(surface_type: str, payload: dict) -> str:
    if surface_type == 'alias':
        return f"alias:{(payload.get('alias') or '').casefold().strip()}"
    if surface_type == 'capability':
        return f"capability:{payload.get('capability_name')}:{payload.get('provider', 'local')}"
    if surface_type == 'transliteration_profile':
        return f"translit:{payload.get('source_script')}->{payload.get('target_script', 'Latn')}"
    if surface_type == 'pronunciation_profile':
        return f"pron:{payload.get('profile_kind', 'default')}"
    if surface_type == 'phonology_profile':
        return f"phon:{payload.get('notation_system', 'broad')}"
    return f"{surface_type}:{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"


def _candidate_score(candidate: dict, source_weights: dict[str, float]) -> float:
    confidence = float(candidate.get('confidence') or 0.0)
    status_factor = STATUS_WEIGHTS.get(candidate.get('status') or 'staged', 0.85)
    surface_factor = SURFACE_WEIGHTS.get(candidate.get('surface_type') or '', 0.9)
    source_factor = source_weights.get(candidate.get('source_name') or '', 0.5)
    return round(confidence * status_factor * surface_factor * source_factor, 6)


def _canonical_already_present(conn, language_id: str, surface_type: str, payload: dict) -> bool:
    if surface_type == 'alias':
        row = conn.execute('SELECT 1 FROM language_aliases WHERE language_id = ? AND alias = ? LIMIT 1', (language_id, payload.get('alias'))).fetchone()
        return row is not None
    if surface_type == 'capability':
        row = conn.execute('SELECT 1 FROM language_capabilities WHERE language_id = ? AND capability_name = ? AND provider = ? LIMIT 1', (language_id, payload.get('capability_name'), payload.get('provider', 'local'))).fetchone()
        return row is not None
    if surface_type == 'transliteration_profile':
        row = conn.execute('SELECT 1 FROM transliteration_profiles WHERE language_id = ? AND source_script = ? AND target_script = ? LIMIT 1', (language_id, payload.get('source_script'), payload.get('target_script', 'Latn'))).fetchone()
        return row is not None
    if surface_type == 'pronunciation_profile':
        row = conn.execute('SELECT 1 FROM pronunciation_profiles WHERE language_id = ? LIMIT 1', (language_id,)).fetchone()
        return row is not None
    if surface_type == 'phonology_profile':
        row = conn.execute('SELECT 1 FROM phonology_profiles WHERE language_id = ? AND notation_system = ? LIMIT 1', (language_id, payload.get('notation_system', 'broad'))).fetchone()
        return row is not None
    return False


def arbitrate_self_fill_candidates(language_id: str | None = None, min_score: float = 0.0, statuses: Iterable[str] = ('staged', 'reviewed')) -> dict:
    statuses = tuple(statuses)
    placeholders = ','.join('?' for _ in statuses)
    params: list = list(statuses)
    query = f"SELECT * FROM self_fill_candidates WHERE status IN ({placeholders})"
    if language_id:
        query += ' AND language_id = ?'
        params.append(language_id)
    query += ' ORDER BY language_id, surface_type, created_at DESC'
    with connect() as conn:
        source_weights = _load_source_weights(conn)
        rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
        grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for row in rows:
            payload = _payload(row)
            row['payload'] = payload
            row['effective_score'] = _candidate_score(row, source_weights)
            grouped[(row['language_id'], row['surface_type'], _group_key(row['surface_type'], payload))].append(row)
        run_id = f"sfar_{uuid.uuid4().hex[:12]}"
        now = utcnow()
        decisions = []
        summary = {'group_count': 0, 'winner_count': 0, 'below_threshold': 0, 'canonical_already_present': 0, 'source_weights': source_weights}
        for (lang_id, surface_type, group_key), group in grouped.items():
            summary['group_count'] += 1
            ranked = sorted(group, key=lambda x: (x['effective_score'], x['confidence'], x['created_at']), reverse=True)
            winner = ranked[0]
            action = 'winner'
            if winner['effective_score'] < min_score:
                action = 'below_threshold'
                summary['below_threshold'] += 1
            elif _canonical_already_present(conn, lang_id, surface_type, winner['payload']):
                action = 'canonical_already_present'
                summary['canonical_already_present'] += 1
            else:
                summary['winner_count'] += 1
            details = {
                'ranked_candidates': [
                    {
                        'candidate_id': item['candidate_id'],
                        'source_name': item['source_name'],
                        'confidence': item['confidence'],
                        'status': item['status'],
                        'effective_score': item['effective_score'],
                    }
                    for item in ranked
                ]
            }
            decision_id = f"sfad_{uuid.uuid4().hex[:12]}"
            conn.execute(
                'INSERT INTO self_fill_arbitration_decisions (decision_id, arbitration_run_id, language_id, surface_type, group_key, winning_candidate_id, winning_score, action, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (decision_id, run_id, lang_id, surface_type, group_key, winner['candidate_id'], winner['effective_score'], action, json.dumps(details, ensure_ascii=False, sort_keys=True), now),
            )
            decisions.append({'decision_id': decision_id, 'language_id': lang_id, 'surface_type': surface_type, 'group_key': group_key, 'winning_candidate_id': winner['candidate_id'], 'winning_score': winner['effective_score'], 'action': action, **details})
        conn.execute('INSERT INTO self_fill_arbitration_runs (arbitration_run_id, mode, language_ids_json, summary_json, created_at) VALUES (?, ?, ?, ?, ?)', (run_id, 'candidate_merge_arbitration', json.dumps([language_id] if language_id else [], ensure_ascii=False), json.dumps(summary, ensure_ascii=False, sort_keys=True), now))
        conn.commit()
    return {'ok': True, 'arbitration_run_id': run_id, 'summary': summary, 'decisions': decisions}


def list_self_fill_arbitration_runs(limit: int = 50) -> dict:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_arbitration_runs ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['language_ids'] = json.loads(row.pop('language_ids_json') or '[]')
        row['summary'] = json.loads(row.pop('summary_json') or '{}')
    return {'ok': True, 'results': rows}


def list_self_fill_arbitration_decisions(arbitration_run_id: str | None = None, limit: int = 100) -> dict:
    with connect() as conn:
        if arbitration_run_id:
            rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_arbitration_decisions WHERE arbitration_run_id = ? ORDER BY created_at DESC LIMIT ?', (arbitration_run_id, limit)).fetchall()]
        else:
            rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_arbitration_decisions ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['details'] = json.loads(row.pop('details_json') or '{}')
    return {'ok': True, 'results': rows}


def promote_arbitrated_self_fill_winners(language_id: str | None = None, min_score: float = 0.35, reviewer: str = 'autofill_arbiter') -> dict:
    arbitration = arbitrate_self_fill_candidates(language_id=language_id, min_score=min_score)
    promoted = []
    skipped = []
    for decision in arbitration['decisions']:
        if decision['action'] != 'winner':
            skipped.append({'decision_id': decision['decision_id'], 'action': decision['action']})
            continue
        result = promote_self_fill_candidate(decision['winning_candidate_id'], reviewer=reviewer)
        promoted.append({'decision_id': decision['decision_id'], 'candidate_id': decision['winning_candidate_id'], 'result': result})
    return {'ok': True, 'arbitration_run_id': arbitration['arbitration_run_id'], 'promoted_count': len(promoted), 'skipped_count': len(skipped), 'promoted': promoted, 'skipped': skipped, 'summary': arbitration['summary']}


def recommend_source_weight(source_name: str, authority_weight: float, notes: str = 'self-fill arbitration override') -> dict:
    return set_source_weight(SourceWeightUpdateRequest(source_name=source_name, authority_weight=authority_weight, notes=notes))
