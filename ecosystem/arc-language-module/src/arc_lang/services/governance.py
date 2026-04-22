from __future__ import annotations
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import ReviewDecisionRequest, CapabilityUpdateRequest, utcnow
from arc_lang.services.manual_lineage import update_custom_lineage_status
from arc_lang.services.onboarding import approve_language_submission

REVIEW_TARGETS = {'language_submission', 'custom_lineage'}
REVIEW_DECISIONS = {'needs_review', 'accepted_local', 'rejected', 'disputed'}
MATURITY_ORDER = {'none': 0, 'seeded': 1, 'experimental': 2, 'reviewed': 3, 'production': 4}


def record_review_decision(req: ReviewDecisionRequest) -> dict:
    """Record a governance review decision for a language submission or custom assertion."""
    if req.target_type not in REVIEW_TARGETS:
        return {'ok': False, 'error': 'invalid_target_type', 'allowed_target_types': sorted(REVIEW_TARGETS)}
    if req.decision not in REVIEW_DECISIONS:
        return {'ok': False, 'error': 'invalid_decision', 'allowed_decisions': sorted(REVIEW_DECISIONS)}

    now = utcnow()
    review_id = f"rev_{uuid.uuid4().hex[:12]}"
    action_result = None
    with connect() as conn:
        conn.execute(
            'INSERT INTO review_decisions (review_id, target_type, target_id, decision, reviewer, confidence, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (review_id, req.target_type, req.target_id, req.decision, req.reviewer, req.confidence, req.notes, now),
        )
        conn.commit()

    if req.target_type == 'language_submission':
        mapped = 'accepted_local' if req.decision == 'accepted_local' else req.decision
        action_result = approve_language_submission(req.target_id, status=mapped)
    elif req.target_type == 'custom_lineage':
        action_result = update_custom_lineage_status(req.target_id, req.decision)

    return {
        'ok': True,
        'review_id': review_id,
        'decision': req.decision,
        'target_type': req.target_type,
        'target_id': req.target_id,
        'action_result': action_result,
    }


def list_review_decisions(target_type: str | None = None, target_id: str | None = None) -> dict:
    """List governance review decisions, optionally filtered by target_type and target_id."""
    clauses=[]
    params=[]
    if target_type:
        clauses.append('target_type = ?')
        params.append(target_type)
    if target_id:
        clauses.append('target_id = ?')
        params.append(target_id)
    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    with connect() as conn:
        rows=[dict(r) for r in conn.execute(f'SELECT * FROM review_decisions {where} ORDER BY created_at DESC', params).fetchall()]
    return {'ok': True, 'results': rows}


def set_language_capability(req: CapabilityUpdateRequest) -> dict:
    """Set a capability maturity record for a language."""
    now = utcnow()
    capability_id = f"cap_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        existing = conn.execute(
            'SELECT capability_id, maturity FROM language_capabilities WHERE language_id = ? AND capability_name = ? AND provider = ?',
            (req.language_id, req.capability_name, req.provider),
        ).fetchone()
        if existing:
            conn.execute(
                'UPDATE language_capabilities SET maturity = ?, confidence = ?, notes = ?, updated_at = ? WHERE capability_id = ?',
                (req.maturity, req.confidence, req.notes, now, existing['capability_id']),
            )
            conn.commit()
            return {'ok': True, 'capability_id': existing['capability_id'], 'updated': True}
        conn.execute(
            'INSERT INTO language_capabilities (capability_id, language_id, capability_name, maturity, confidence, provider, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (capability_id, req.language_id, req.capability_name, req.maturity, req.confidence, req.provider, req.notes, now),
        )
        conn.commit()
    return {'ok': True, 'capability_id': capability_id, 'updated': False}


def list_language_capabilities(language_id: str | None = None) -> dict:
    """List language capability records, optionally filtered by language_id."""
    with connect() as conn:
        if language_id:
            rows=[dict(r) for r in conn.execute('SELECT * FROM language_capabilities WHERE language_id = ? ORDER BY capability_name, provider', (language_id,)).fetchall()]
        else:
            rows=[dict(r) for r in conn.execute('SELECT * FROM language_capabilities ORDER BY language_id, capability_name, provider').fetchall()]
    return {'ok': True, 'results': rows}


def get_language_readiness(language_id: str) -> dict:
    """Return the full readiness summary for a language (all capabilities + maturity)."""
    with connect() as conn:
        lang = conn.execute('SELECT language_id, name FROM languages WHERE language_id = ?', (language_id,)).fetchone()
        if not lang:
            return {'ok': False, 'error': 'language_not_found', 'language_id': language_id}
        caps = [dict(r) for r in conn.execute('SELECT capability_name, maturity, confidence, provider, notes FROM language_capabilities WHERE language_id = ?', (language_id,)).fetchall()]
    if not caps:
        overall = 'none'
    else:
        overall = max(caps, key=lambda c: MATURITY_ORDER.get(c['maturity'], -1))['maturity']
    return {
        'ok': True,
        'language_id': lang['language_id'],
        'name': lang['name'],
        'overall_maturity': overall,
        'capabilities': caps,
    }
