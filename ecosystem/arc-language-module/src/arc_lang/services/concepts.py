
from __future__ import annotations
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import SemanticConceptUpsertRequest, ConceptLinkRequest, utcnow


def upsert_semantic_concept(req: SemanticConceptUpsertRequest) -> dict:
    """Create or update a semantic concept with label, domain, description, and confidence."""
    now = utcnow()
    concept_id = req.concept_id or f"concept_{req.domain}_{req.canonical_label.casefold().replace(' ','_')}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO semantic_concepts (concept_id, canonical_label, domain, description, source_name, source_ref, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concept_id) DO UPDATE SET canonical_label=excluded.canonical_label, domain=excluded.domain, description=excluded.description, source_name=excluded.source_name, source_ref=excluded.source_ref, confidence=excluded.confidence, updated_at=excluded.updated_at
            """,
            (concept_id, req.canonical_label, req.domain, req.description, req.source_name, req.source_ref, req.confidence, now, now),
        )
        conn.commit()
    return {'ok': True, 'concept_id': concept_id, 'canonical_label': req.canonical_label, 'domain': req.domain}


def link_concept(req: ConceptLinkRequest) -> dict:
    """Link a concept to a target (lexeme, language, phrase_key, or alias)."""
    now = utcnow()
    link_id = f"clink_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        concept = conn.execute("SELECT concept_id FROM semantic_concepts WHERE concept_id=?", (req.concept_id,)).fetchone()
        if not concept:
            return {'ok': False, 'error': 'concept_not_found', 'concept_id': req.concept_id}
        exists = False
        if req.target_type == 'lexeme':
            exists = conn.execute("SELECT 1 FROM lexemes WHERE lexeme_id=?", (req.target_id,)).fetchone() is not None
        elif req.target_type == 'language':
            exists = conn.execute("SELECT 1 FROM languages WHERE language_id=?", (req.target_id,)).fetchone() is not None
        elif req.target_type == 'phrase_key':
            exists = conn.execute("SELECT 1 FROM phrase_translations WHERE canonical_key=? LIMIT 1", (req.target_id,)).fetchone() is not None
        elif req.target_type == 'alias':
            exists = conn.execute("SELECT 1 FROM language_aliases WHERE alias_id=?", (req.target_id,)).fetchone() is not None
        if not exists:
            return {'ok': False, 'error': 'target_not_found', 'target_type': req.target_type, 'target_id': req.target_id}
        conn.execute(
            """
            INSERT INTO concept_links (link_id, concept_id, target_type, target_id, relation, confidence, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (link_id, req.concept_id, req.target_type, req.target_id, req.relation, req.confidence, req.notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'link_id': link_id, 'concept_id': req.concept_id, 'target_type': req.target_type, 'target_id': req.target_id}


def list_semantic_concepts(domain: str | None = None, q: str | None = None) -> dict:
    """List semantic concepts, optionally filtered by domain or query string."""
    query = "SELECT * FROM semantic_concepts"
    params = []
    clauses = []
    if domain:
        clauses.append('domain=?')
        params.append(domain)
    if q:
        clauses.append('(canonical_label LIKE ? OR description LIKE ?)')
        like = f"%{q}%"
        params.extend([like, like])
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY domain, canonical_label'
    with connect() as conn:
        items = [dict(r) for r in conn.execute(query, params).fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}


def get_concept_bundle(concept_id: str) -> dict:
    """Return a concept with all its concept_links in a single bundle."""
    with connect() as conn:
        concept = conn.execute("SELECT * FROM semantic_concepts WHERE concept_id=?", (concept_id,)).fetchone()
        if not concept:
            return {'ok': False, 'error': 'concept_not_found', 'concept_id': concept_id}
        links = [dict(r) for r in conn.execute("SELECT * FROM concept_links WHERE concept_id=? ORDER BY target_type, target_id", (concept_id,)).fetchall()]
    return {'ok': True, 'concept': dict(concept), 'links': links, 'count': len(links)}
