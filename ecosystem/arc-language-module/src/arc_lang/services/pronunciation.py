from __future__ import annotations

import json
import re
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import PronunciationRequest, utcnow
from arc_lang.services.detection import detect_language, detect_script
from arc_lang.services.transliteration import transliterate


def _fetch_profile(language_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT profile_id, language_id, profile_kind, romanization_scheme, ipa_hint, examples_json, notes FROM pronunciation_profiles WHERE language_id = ? ORDER BY profile_kind LIMIT 1",
            (language_id,),
        ).fetchone()
    if not row:
        return None
    out = dict(row)
    out['examples'] = json.loads(out.get('examples_json') or '{}')
    out.pop('examples_json', None)
    return out


def upsert_pronunciation_profile(language_id: str, profile_kind: str, romanization_scheme: str | None, ipa_hint: str | None, examples: dict[str, str], notes: str = '') -> dict:
    """Create or update a pronunciation profile (romanization scheme, IPA hint, examples) for a language."""
    now = utcnow()
    profile_id = f"pron_{uuid.uuid5(uuid.NAMESPACE_URL, language_id + ':' + profile_kind).hex[:18]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO pronunciation_profiles (profile_id, language_id, profile_kind, romanization_scheme, ipa_hint, examples_json, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET romanization_scheme=excluded.romanization_scheme, ipa_hint=excluded.ipa_hint, examples_json=excluded.examples_json, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (profile_id, language_id, profile_kind, romanization_scheme, ipa_hint, json.dumps(examples, ensure_ascii=False), notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'profile_id': profile_id, 'language_id': language_id}


def list_pronunciation_profiles(language_id: str | None = None) -> dict:
    """List pronunciation profiles, optionally filtered by language_id."""
    query = "SELECT profile_id, language_id, profile_kind, romanization_scheme, ipa_hint, examples_json, notes, created_at, updated_at FROM pronunciation_profiles"
    params = []
    if language_id:
        query += " WHERE language_id = ?"
        params.append(language_id)
    query += " ORDER BY language_id, profile_kind"
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    for row in rows:
        row['examples'] = json.loads(row.pop('examples_json')) if row.get('examples_json') else {}
    return {'ok': True, 'results': rows}


def pronunciation_guide(req: PronunciationRequest) -> dict:
    """Return pronunciation guidance for text in a language, from seeded pronunciation profiles."""
    detection = None
    language_id = req.language_id
    if not language_id and req.allow_detect:
        detection = detect_language(req.text)
        language_id = detection.winner_language_id
    if not language_id:
        return {'ok': False, 'error': 'source_language_unknown', 'detection': detection.model_dump() if detection else None}

    profile = _fetch_profile(language_id)
    source_script = detect_script(req.text)
    translit = None
    if source_script and source_script != req.target_script:
        translit = transliterate(req.text, source_script, req.target_script)
    spoken = req.text
    matched_example = None
    if profile:
        examples = profile.get('examples', {})
        matched_example = examples.get(req.text) or examples.get(req.text.casefold())
        if matched_example:
            spoken = matched_example
        elif translit and translit.get('ok'):
            spoken = translit['result']
    elif translit and translit.get('ok'):
        spoken = translit['result']

    syllables = [t for t in re.split(r"[-\s]+", spoken) if t]
    return {
        'ok': True,
        'language_id': language_id,
        'text': req.text,
        'pronunciation_text': spoken,
        'source_script': source_script,
        'target_script': req.target_script,
        'profile': profile,
        'matched_example': matched_example,
        'transliteration': translit,
        'syllable_like_units': syllables,
        'detection': detection.model_dump() if detection else None,
        'notes': [
            'Pronunciation output is a broad hint layer, not a strict phonology engine.',
            'Use speech providers for optional audio playback when runtime support exists.',
        ],
    }
