from __future__ import annotations

import re
from arc_lang.core.db import connect
from arc_lang.core.models import AnalysisRequest, PronunciationRequest
from arc_lang.services.detection import detect_language, detect_script
from arc_lang.services.transliteration import transliterate, list_transliteration_profiles
from arc_lang.services.pronunciation import pronunciation_guide

WORD_RE = re.compile(r"\w+", re.UNICODE)


def analyze_text(req: AnalysisRequest) -> dict:
    """Full linguistic analysis: script, tokens, lexeme lookup, transliteration, and pronunciation hints."""
    detection = None
    language_id = req.language_id
    if not language_id and req.allow_detect:
        detection = detect_language(req.text)
        language_id = detection.winner_language_id
    script = detect_script(req.text)
    tokens = WORD_RE.findall(req.text)
    token_rows = []
    phrase_match = None
    with connect() as conn:
        if language_id:
            phrase_row = conn.execute(
                "SELECT canonical_key, language_id, text_value, register FROM phrase_translations WHERE language_id = ? AND lower(text_value) = lower(?) LIMIT 1",
                (language_id, req.text),
            ).fetchone()
            if phrase_row:
                phrase_match = dict(phrase_row)
        for token in tokens:
            row = None
            if language_id:
                row = conn.execute(
                    "SELECT lexeme_id, lemma, gloss, canonical_meaning_key FROM lexemes WHERE language_id = ? AND lower(lemma)=lower(?) LIMIT 1",
                    (language_id, token),
                ).fetchone()
            token_rows.append({
                'token': token,
                'normalized': token.casefold(),
                'lexeme': dict(row) if row else None,
                'shape': 'alphabetic' if token.isalpha() else 'mixed',
            })
    translit = None
    if script and script != 'Latn':
        translit = transliterate(req.text, script, 'Latn')
    pronunciation = None
    if req.include_pronunciation:
        pronunciation = pronunciation_guide(PronunciationRequest(text=req.text, language_id=language_id, allow_detect=False, target_script='Latn'))
    transliteration_profiles = list_transliteration_profiles(language_id=language_id).get('results', []) if language_id else []
    return {
        'ok': True,
        'text': req.text,
        'language_id': language_id,
        'script': script,
        'token_count': len(tokens),
        'tokens': token_rows,
        'phrase_match': phrase_match,
        'transliteration': translit,
        'pronunciation': pronunciation,
        'transliteration_profiles': transliteration_profiles,
        'detection': detection.model_dump() if detection else None,
        'notes': [
            'This is a seeded morphology/syntax assist layer, not a full parser.',
            'Lexeme matching is exact seeded lookup plus script and transliteration context.',
        ],
    }
