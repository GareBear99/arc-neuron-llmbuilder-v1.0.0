from __future__ import annotations
from arc_lang.core.db import connect


def get_etymology(language_id: str, lemma: str) -> dict:
    """Return etymology edges for a given lemma in a language."""
    with connect() as conn:
        lex = conn.execute(
            "SELECT lexeme_id, language_id, lemma, gloss, canonical_meaning_key FROM lexemes WHERE language_id = ? AND lower(lemma) = lower(?) LIMIT 1",
            (language_id, lemma),
        ).fetchone()
        if not lex:
            return {"ok": False, "error": "lexeme_not_found", "language_id": language_id, "lemma": lemma}
        edges = [dict(r) for r in conn.execute(
            "SELECT etymology_id, child_lexeme_id, parent_lexeme_id, relation, confidence, source_ref FROM etymology_edges WHERE child_lexeme_id = ?",
            (lex['lexeme_id'],),
        ).fetchall()]
        parents = []
        for edge in edges:
            parent = conn.execute(
                "SELECT lexeme_id, language_id, lemma, gloss, canonical_meaning_key FROM lexemes WHERE lexeme_id = ?",
                (edge['parent_lexeme_id'],),
            ).fetchone()
            if parent:
                parents.append({"edge": edge, "parent": dict(parent)})
        prov = [dict(r) for r in conn.execute(
            "SELECT source_name, source_ref, confidence, notes FROM provenance_records WHERE record_type = 'lexeme' AND record_id = ? ORDER BY confidence DESC",
            (lex['lexeme_id'],),
        ).fetchall()]
    return {"ok": True, "lexeme": dict(lex), "parents": parents, "provenance": prov}
