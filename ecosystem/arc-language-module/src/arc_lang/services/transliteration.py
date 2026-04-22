from __future__ import annotations

import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import TransliterationRequest, utcnow
from arc_lang.services.detection import detect_script, detect_language

BASIC_MAPS = {
    ("Cyrl", "Latn"): {
        "А": "A", "а": "a", "Б": "B", "б": "b", "В": "V", "в": "v",
        "Г": "G", "г": "g", "Д": "D", "д": "d", "Е": "E", "е": "e",
        "Ё": "Yo", "ё": "yo", "Ж": "Zh", "ж": "zh", "З": "Z", "з": "z",
        "И": "I", "и": "i", "Й": "Y", "й": "y", "К": "K", "к": "k",
        "Л": "L", "л": "l", "М": "M", "м": "m", "Н": "N", "н": "n",
        "О": "O", "о": "o", "П": "P", "п": "p", "Р": "R", "р": "r",
        "С": "S", "с": "s", "Т": "T", "т": "t", "У": "U", "у": "u",
        "Ф": "F", "ф": "f", "Х": "Kh", "х": "kh", "Ц": "Ts", "ц": "ts",
        "Ч": "Ch", "ч": "ch", "Ш": "Sh", "ш": "sh", "Щ": "Shch", "щ": "shch",
        "Ы": "Y", "ы": "y", "Э": "E", "э": "e", "Ю": "Yu", "ю": "yu",
        "Я": "Ya", "я": "ya", "Ь": "", "ь": "", "Ъ": "", "ъ": "",
    },
    ("Cher", "Latn"): {
        "Ꭳ": "o", "Ꮟ": "si", "Ᏺ": "yo", "Ꮳ": "tsa", "Ꮃ": "la", "Ꭹ": "gi",
        "Ꭰ": "a", "Ꭱ": "e", "Ꭲ": "i", "Ꭴ": "u", "Ꭵ": "v", "Ꮢ": "sv", "Ꮅ": "li",
    },
    ("Deva", "Latn"): {
        "अ":"a","आ":"aa","इ":"i","ई":"ii","उ":"u","ऊ":"uu","ए":"e","ओ":"o","क":"k","ख":"kh","ग":"g","घ":"gh","च":"ch","ज":"j","ट":"t","ड":"d","त":"t","द":"d","न":"n","प":"p","ब":"b","म":"m","य":"y","र":"r","ल":"l","व":"v","श":"sh","स":"s","ह":"h","ध":"dh","थ":"th","भ":"bh","ञ":"ny","ं":"n","ा":"aa","ि":"i","ी":"ii","ु":"u","ू":"uu","े":"e","ो":"o","्":""
    },
    ("Arab", "Latn"): {
        "ا":"a","ب":"b","ت":"t","ث":"th","ج":"j","ح":"h","خ":"kh","د":"d","ذ":"dh","ر":"r","ز":"z","س":"s","ش":"sh","ص":"s","ض":"d","ط":"t","ظ":"z","ع":"a","غ":"gh","ف":"f","ق":"q","ك":"k","ل":"l","م":"m","ن":"n","ه":"h","و":"w","ي":"y","ء":"'","ى":"a","ة":"a","َ":"a","ُ":"u","ِ":"i","ّ":"","ْ":""
    },
    ("Hebr", "Latn"): {
        "א":"a","ב":"b","ג":"g","ד":"d","ה":"h","ו":"v","ז":"z","ח":"kh","ט":"t","י":"y","כ":"k","ך":"k","ל":"l","מ":"m","ם":"m","נ":"n","ן":"n","ס":"s","ע":"a","פ":"p","ף":"p","צ":"ts","ץ":"ts","ק":"q","ר":"r","ש":"sh","ת":"t"
    },
}

def _profile_lookup(language_id: str | None, source_script: str, target_script: str) -> dict | None:
    if language_id:
        with connect() as conn:
            row = conn.execute(
                "SELECT profile_id, language_id, source_script, target_script, scheme_name, coverage, example_in, example_out, notes FROM transliteration_profiles WHERE language_id = ? AND source_script = ? AND target_script = ? LIMIT 1",
                (language_id, source_script, target_script),
            ).fetchone()
            if row:
                return dict(row)
    with connect() as conn:
        row = conn.execute(
            "SELECT profile_id, language_id, source_script, target_script, scheme_name, coverage, example_in, example_out, notes FROM transliteration_profiles WHERE source_script = ? AND target_script = ? LIMIT 1",
            (source_script, target_script),
        ).fetchone()
    return dict(row) if row else None

def list_transliteration_profiles(language_id: str | None = None) -> dict:
    """List transliteration profiles, optionally filtered by language_id."""
    query = "SELECT profile_id, language_id, source_script, target_script, scheme_name, coverage, example_in, example_out, notes, created_at, updated_at FROM transliteration_profiles"
    params = []
    if language_id:
        query += " WHERE language_id = ?"
        params.append(language_id)
    query += " ORDER BY language_id, source_script, target_script"
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    return {"ok": True, "results": rows}

def upsert_transliteration_profile(language_id: str, source_script: str, target_script: str, scheme_name: str, coverage: str, example_in: str | None = None, example_out: str | None = None, notes: str = "") -> dict:
    """Create or update a transliteration profile for a language+script pair."""
    profile_id = f"trprof_{uuid.uuid5(uuid.NAMESPACE_URL, language_id + ':' + source_script + ':' + target_script + ':' + scheme_name).hex[:18]}"
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO transliteration_profiles (profile_id, language_id, source_script, target_script, scheme_name, coverage, example_in, example_out, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET scheme_name=excluded.scheme_name, coverage=excluded.coverage, example_in=excluded.example_in, example_out=excluded.example_out, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (profile_id, language_id, source_script, target_script, scheme_name, coverage, example_in, example_out, notes, now, now),
        )
        conn.commit()
    return {"ok": True, "profile_id": profile_id, "language_id": language_id}

def transliterate(text: str, source_script: str, target_script: str = "Latn", language_id: str | None = None) -> dict:
    """Transliterate text from a source script to a target script using seeded mapping tables."""
    mapping = BASIC_MAPS.get((source_script, target_script))
    profile = _profile_lookup(language_id, source_script, target_script)
    if not mapping:
        return {
            "ok": False,
            "source_script": source_script,
            "target_script": target_script,
            "result": text,
            "reason": "no_mapping_registered",
            "profile": profile,
        }
    result = "".join(mapping.get(ch, ch) for ch in text)
    return {
        "ok": True,
        "source_script": source_script,
        "target_script": target_script,
        "result": result,
        "reason": "basic_registered_mapping",
        "profile": profile,
    }

def transliterate_request(req: TransliterationRequest) -> dict:
    """Transliterate using a full TransliterationRequest model (with language detection support)."""
    detection = None
    language_id = req.language_id
    if not language_id and req.allow_detect:
        detection = detect_language(req.text)
        language_id = detection.winner_language_id
    source_script = req.source_script or detect_script(req.text) or "Latn"
    out = transliterate(req.text, source_script, req.target_script, language_id=language_id)
    out.update({
        "text": req.text,
        "language_id": language_id,
        "detection": detection.model_dump() if detection else None,
    })
    return out
