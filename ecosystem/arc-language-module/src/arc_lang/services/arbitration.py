from __future__ import annotations
from collections import defaultdict
from arc_lang.core.db import connect

# Fallback weights used only when source_weights table is empty or source is unknown.
# These are also the seeded defaults — operators can override via set-source-weight CLI.
_FALLBACK_SOURCE_WEIGHTS: dict[str, float] = {
    'iso639_3': 1.0,
    'glottolog': 0.95,
    'cldr': 0.9,
    'common_seed': 0.85,
    'canonical_import': 1.0,
    'common_seed_local': 0.7,
    'user_submission': 0.65,
    'user_custom': 0.55,
    'local': 0.6,
}

STATUS_WEIGHTS = {
    None: 1.0,
    'canonical': 1.0,        # source-backed canonical lineage edges
    'user_asserted': 0.65,
    'needs_review': 0.55,
    'accepted_local': 1.0,
    'rejected': 0.15,
    'disputed': 0.45,
}
DECISION_WEIGHTS = {
    None: 1.0,
    'needs_review': 0.7,
    'accepted_local': 1.2,
    'rejected': 0.1,
    'disputed': 0.5,
}


def _load_source_weights(conn) -> dict[str, float]:
    """Load authority weights from DB, merging over fallback defaults.
    DB values always win over fallback defaults.
    Unknown sources receive a default of 0.75.
    """
    db_weights = {r['source_name']: r['authority_weight'] for r in conn.execute(
        "SELECT source_name, authority_weight FROM source_weights"
    ).fetchall()}
    merged = {**_FALLBACK_SOURCE_WEIGHTS, **db_weights}
    return merged


def _source_weight_from(source_name: str | None, weights: dict[str, float]) -> float:
    """Return the authority weight for a source name from the provided weights dict."""
    if not source_name:
        return 0.75
    # Exact match first
    if source_name in weights:
        return weights[source_name]
    # Prefix match (e.g. 'common_seed_local' matches 'common_seed')
    for prefix, weight in weights.items():
        if source_name.startswith(prefix):
            return weight
    return 0.75


def _latest_decision(conn, target_type: str, target_id: str) -> str | None:
    """Return the latest review decision for a target entity, or None."""
    row = conn.execute(
        'SELECT decision FROM review_decisions WHERE target_type = ? AND target_id = ? ORDER BY created_at DESC LIMIT 1',
        (target_type, target_id),
    ).fetchone()
    return row['decision'] if row else None


def _fetch_name(conn, entity_id: str) -> str | None:
    """Return the human-readable name for a language or lineage node ID."""
    if entity_id.startswith('lang:'):
        row = conn.execute('SELECT name FROM languages WHERE language_id = ?', (entity_id,)).fetchone()
        return row['name'] if row else None
    row = conn.execute('SELECT name FROM lineage_nodes WHERE node_id = ?', (entity_id,)).fetchone()
    return row['name'] if row else None


def _canonical_claims(conn, language_id: str) -> list[dict]:
    """Collect all canonical lineage claims (from lineage_edges + implicit family/branch) for a language."""
    claims = []
    rows = conn.execute(
        '''
        SELECT e.edge_id as claim_id, e.src_id, e.dst_id, e.relation, e.confidence, e.disputed,
               COALESCE(p.source_name, 'canonical_import') as source_name,
               COALESCE(p.source_ref, e.source_ref) as source_ref,
               p.notes as provenance_notes,
               e.created_at,
               'canonical' as claim_type
        FROM lineage_edges e
        LEFT JOIN provenance_records p
          ON p.record_type = 'language' AND p.record_id = e.src_id
        WHERE e.src_id = ?
        ORDER BY e.created_at ASC
        ''',
        (language_id,),
    ).fetchall()
    for row in rows:
        d = dict(row)
        d['status'] = 'canonical'
        d['review_decision'] = None
        claims.append(d)
    lang = conn.execute(
        '''
        SELECT l.language_id, l.name, l.family, l.branch, l.family_node_id, l.branch_node_id,
               COALESCE(p.source_name, 'canonical_import') as source_name,
               COALESCE(p.source_ref, '') as source_ref,
               COALESCE(p.notes, '') as provenance_notes
        FROM languages l
        LEFT JOIN provenance_records p
          ON p.record_type = 'language' AND p.record_id = l.language_id
        WHERE l.language_id = ?
        ORDER BY p.confidence DESC
        LIMIT 1
        ''',
        (language_id,),
    ).fetchone()
    if lang and lang['branch_node_id']:
        claims.append({
            'claim_id': f"implicit_branch::{lang['language_id']}",
            'src_id': lang['language_id'],
            'dst_id': lang['branch_node_id'],
            'relation': 'member_of_branch',
            'confidence': 0.9,
            'disputed': 0,
            'source_name': lang['source_name'],
            'source_ref': lang['source_ref'],
            'provenance_notes': 'Implicit branch claim from language row',
            'created_at': '',
            'claim_type': 'canonical',
            'status': 'canonical',
            'review_decision': None,
        })
    if lang and lang['family_node_id']:
        claims.append({
            'claim_id': f"implicit_family::{lang['language_id']}",
            'src_id': lang['language_id'],
            'dst_id': lang['family_node_id'],
            'relation': 'member_of_family',
            'confidence': 0.9,
            'disputed': 0,
            'source_name': lang['source_name'],
            'source_ref': lang['source_ref'],
            'provenance_notes': 'Implicit family claim from language row',
            'created_at': '',
            'claim_type': 'canonical',
            'status': 'canonical',
            'review_decision': None,
        })
    return claims


def _custom_claims(conn, language_id: str) -> list[dict]:
    """Collect all custom lineage assertion claims for a language."""
    claims = []
    rows = conn.execute(
        '''
        SELECT assertion_id as claim_id, src_id, dst_id, relation, confidence, disputed,
               source_name, source_ref, notes as provenance_notes,
               created_at, status,
               'custom' as claim_type
        FROM custom_lineage_assertions
        WHERE src_id = ?
        ORDER BY created_at ASC
        ''',
        (language_id,),
    ).fetchall()
    for row in rows:
        d = dict(row)
        d['review_decision'] = _latest_decision(conn, 'custom_lineage', d['claim_id'])
        claims.append(d)
    return claims


def _score_claim(claim: dict, source_weights: dict[str, float]) -> float:
    """Compute the effective arbitration score for a single lineage claim."""
    base = float(claim.get('confidence') or 0.0)
    source_factor = _source_weight_from(claim.get('source_name'), source_weights)
    status_factor = STATUS_WEIGHTS.get(claim.get('status'), 0.75)
    decision_factor = DECISION_WEIGHTS.get(claim.get('review_decision'), 1.0)
    dispute_factor = 0.6 if int(claim.get('disputed') or 0) else 1.0
    score = base * source_factor * status_factor * decision_factor * dispute_factor
    return round(score, 6)


def _relation_bucket(relation: str) -> str:
    """Map a lineage relation string to a canonical bucket name (family/branch/parent)."""
    if 'family' in relation:
        return 'family'
    if 'branch' in relation:
        return 'branch'
    if relation in {'child_of', 'dialect_of', 'descends_from', 'parent_of'}:
        return 'parent'
    return relation


def resolve_effective_lineage(language_id: str) -> dict:
    """Resolve effective lineage for a language via weighted arbitration of canonical and custom claims."""
    with connect() as conn:
        # Always load current DB weights — operator changes via set-source-weight take effect here
        source_weights = _load_source_weights(conn)
        lang = conn.execute(
            'SELECT language_id, name, family, branch, family_node_id, branch_node_id, parent_language_id FROM languages WHERE language_id = ?',
            (language_id,),
        ).fetchone()
        if not lang:
            return {'ok': False, 'error': 'language_not_found', 'language_id': language_id}
        claims = _canonical_claims(conn, language_id) + _custom_claims(conn, language_id)
        for claim in claims:
            claim['dst_name'] = _fetch_name(conn, claim['dst_id'])
            claim['src_name'] = _fetch_name(conn, claim['src_id'])
            claim['bucket'] = _relation_bucket(claim['relation'])
            claim['effective_score'] = _score_claim(claim, source_weights)
        grouped: dict[str, list[dict]] = defaultdict(list)
        for claim in claims:
            grouped[claim['bucket']].append(claim)
        winners = {}
        conflicts = []
        for bucket, bucket_claims in grouped.items():
            ordered = sorted(bucket_claims, key=lambda c: (c['effective_score'], c['confidence']), reverse=True)
            winner = ordered[0]
            runner_up = ordered[1] if len(ordered) > 1 else None
            margin = None if not runner_up else round(winner['effective_score'] - runner_up['effective_score'], 6)
            conflict = bool(runner_up and winner['dst_id'] != runner_up['dst_id'] and margin is not None and margin < 0.2)
            winners[bucket] = {
                'bucket': bucket,
                'winner': winner,
                'runner_up': runner_up,
                'margin': margin,
                'conflict': conflict,
            }
            if conflict:
                conflicts.append({
                    'bucket': bucket,
                    'winner_claim_id': winner['claim_id'],
                    'winner_dst_id': winner['dst_id'],
                    'runner_up_claim_id': runner_up['claim_id'],
                    'runner_up_dst_id': runner_up['dst_id'],
                    'margin': margin,
                })
        return {
            'ok': True,
            'language': dict(lang),
            'claims': sorted(claims, key=lambda c: (c['bucket'], -c['effective_score'], c['dst_id'])),
            'effective_truth': winners,
            'conflicts': conflicts,
            'policy': {
                'source_weights': source_weights,   # now reflects live DB state
                'status_weights': STATUS_WEIGHTS,
                'decision_weights': DECISION_WEIGHTS,
                'conflict_margin_lt': 0.2,
            },
        }

