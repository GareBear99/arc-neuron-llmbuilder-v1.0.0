from __future__ import annotations
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import TranslationExplainRequest, utcnow


def create_translation_assertion(req: TranslationExplainRequest) -> dict:
    """Create and store a translation assertion with provenance."""
    assertion_id = f"ta_{uuid.uuid4().hex[:12]}"
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO translation_assertions (
                assertion_id, source_language_id, target_language_id, source_text,
                translated_text, confidence, rationale, provider, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assertion_id, req.source_language_id, req.target_language_id, req.source_text,
                req.translated_text, req.confidence, req.rationale, req.provider, now,
            ),
        )
        conn.commit()
    return {
        "ok": True,
        "assertion_id": assertion_id,
        "source_language_id": req.source_language_id,
        "target_language_id": req.target_language_id,
        "confidence": req.confidence,
        "rationale": req.rationale,
    }
