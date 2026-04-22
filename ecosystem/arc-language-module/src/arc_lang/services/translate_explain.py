from __future__ import annotations
from arc_lang.core.db import connect
from arc_lang.core.models import TranslateExplainQuery
from arc_lang.services.detection import detect_language
from arc_lang.services.lineage import get_lineage
from arc_lang.services.etymology import get_etymology
from arc_lang.services.linguistic_analysis import analyze_text
from arc_lang.services.pronunciation import pronunciation_guide
from arc_lang.core.models import AnalysisRequest, PronunciationRequest


def _find_canonical_key(conn, source_language_id: str, text: str) -> str | None:
    """Find the canonical phrase key for a text in a source language."""
    row = conn.execute(
        """
        SELECT canonical_key FROM phrase_translations
        WHERE language_id = ? AND lower(text_value) = lower(?)
        LIMIT 1
        """,
        (source_language_id, text),
    ).fetchone()
    return row["canonical_key"] if row else None


def _find_lexeme(conn, language_id: str, lemma: str):
    """Find a lexeme record by language and lemma."""
    return conn.execute(
        "SELECT lexeme_id, language_id, lemma, gloss, canonical_meaning_key FROM lexemes WHERE language_id = ? AND lower(lemma) = lower(?) LIMIT 1",
        (language_id, lemma),
    ).fetchone()


def translate_explain(query: TranslateExplainQuery) -> dict:
    """Look up a phrase translation and return it with etymology, lineage, and pronunciation context."""
    source_language_id = query.source_language_id
    detection = None
    if not source_language_id and query.allow_detect:
        detection = detect_language(query.text)
        source_language_id = detection.winner_language_id
    if not source_language_id:
        return {
            "ok": False,
            "error": "source_language_unknown",
            "detection": detection.model_dump() if detection else None,
        }

    with connect() as conn:
        canonical_key = _find_canonical_key(conn, source_language_id, query.text)
        source_lex = _find_lexeme(conn, source_language_id, query.text)
        if not canonical_key and source_lex and source_lex['canonical_meaning_key']:
            canonical_key = source_lex['canonical_meaning_key']
        if not canonical_key:
            return {
                "ok": False,
                "error": "no_phrase_translation_found",
                "source_language_id": source_language_id,
                "target_language_id": query.target_language_id,
                "detection": detection.model_dump() if detection else None,
            }
        out = conn.execute(
            """
            SELECT phrase_id, text_value, register FROM phrase_translations
            WHERE canonical_key = ? AND language_id = ?
            LIMIT 1
            """,
            (canonical_key, query.target_language_id),
        ).fetchone()
        if not out:
            target_lex = conn.execute(
                "SELECT lexeme_id, lemma FROM lexemes WHERE language_id = ? AND canonical_meaning_key = ? LIMIT 1",
                (query.target_language_id, canonical_key),
            ).fetchone()
            if target_lex:
                out = {'phrase_id': target_lex['lexeme_id'], 'text_value': target_lex['lemma'], 'register': 'lexeme_fallback'}
        if not out:
            return {
                "ok": False,
                "error": "target_phrase_missing",
                "canonical_key": canonical_key,
                "source_language_id": source_language_id,
                "target_language_id": query.target_language_id,
            }
        prov = [dict(r) for r in conn.execute(
            "SELECT source_name, source_ref, confidence, notes FROM provenance_records WHERE record_type IN ('phrase_translation','lexeme') AND record_id = ?",
            (out["phrase_id"],),
        ).fetchall()]

    etymology = get_etymology(source_language_id, query.text)
    source_analysis = analyze_text(AnalysisRequest(text=query.text, language_id=source_language_id, allow_detect=False, include_pronunciation=True))
    target_pronunciation = pronunciation_guide(PronunciationRequest(text=out['text_value'], language_id=query.target_language_id, allow_detect=False, target_script='Latn'))
    rationale = "Matched canonical meaning key and resolved target rendering with provenance."
    if etymology.get('ok'):
        rationale += " Source lexeme has etymology data attached."

    return {
        "ok": True,
        "mode": "seed_phrase_translation",
        "canonical_key": canonical_key,
        "source_language_id": source_language_id,
        "target_language_id": query.target_language_id,
        "source_text": query.text,
        "translated_text": out["text_value"],
        "register": out["register"],
        "source_lineage": get_lineage(source_language_id),
        "target_lineage": get_lineage(query.target_language_id),
        "source_etymology": etymology,
        "detection": detection.model_dump() if detection else None,
        "provenance": prov,
        "source_analysis": source_analysis,
        "target_pronunciation": target_pronunciation,
        "rationale": rationale,
    }
