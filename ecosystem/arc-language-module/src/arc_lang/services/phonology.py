from __future__ import annotations
import json
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow


def upsert_phonology_profile(language_id: str, notation_system: str, broad_ipa: str | None = None, stress_policy: str | None = None, syllable_template: str | None = None, examples: dict | None = None, notes: str = '') -> dict:
    """Create or update a phonology profile (broad IPA, stress, syllable template) for a language."""
    now = utcnow()
    profile_id = f"phon_{uuid.uuid5(uuid.NAMESPACE_URL, language_id + ':' + notation_system).hex[:18]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO phonology_profiles (profile_id, language_id, notation_system, broad_ipa, stress_policy, syllable_template, examples_json, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET broad_ipa=excluded.broad_ipa, stress_policy=excluded.stress_policy, syllable_template=excluded.syllable_template, examples_json=excluded.examples_json, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (profile_id, language_id, notation_system, broad_ipa, stress_policy, syllable_template, json.dumps(examples or {}, ensure_ascii=False), notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'profile_id': profile_id}


def list_phonology_profiles(language_id: str | None = None) -> dict:
    """List phonology profiles, optionally filtered by language_id."""
    q = 'SELECT * FROM phonology_profiles'
    params = []
    if language_id:
        q += ' WHERE language_id = ?'
        params.append(language_id)
    q += ' ORDER BY language_id, notation_system'
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, tuple(params)).fetchall()]
    for row in rows:
        row['examples'] = json.loads(row.pop('examples_json') or '{}')
    return {'ok': True, 'results': rows}


def phonology_hint(text: str, language_id: str) -> dict:
    """Return a phonology hint for text in a given language, from the seeded phonology profile."""
    profiles = list_phonology_profiles(language_id).get('results', [])
    if not profiles:
        return {'ok': False, 'error': 'phonology_profile_not_found', 'language_id': language_id}
    profile = profiles[0]
    examples = profile.get('examples', {})
    return {
        'ok': True,
        'language_id': language_id,
        'text': text,
        'notation_system': profile['notation_system'],
        'broad_ipa': examples.get(text, profile.get('broad_ipa')),
        'stress_policy': profile.get('stress_policy'),
        'syllable_template': profile.get('syllable_template'),
        'notes': profile.get('notes', ''),
    }
