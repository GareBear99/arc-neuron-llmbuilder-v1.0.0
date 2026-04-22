from __future__ import annotations
import json
import re
from collections import Counter
from arc_lang.core.db import connect
from arc_lang.core.models import DetectionResult

WORD_RE = re.compile(r"\w+", re.UNICODE)
SCRIPT_RANGES: list[tuple[str, list[tuple[int, int]]]] = [
    ("Cyrl", [(1024, 1279)]),
    ("Arab", [(1536, 1791), (1872, 1919), (64336, 65023)]),
    ("Deva", [(2304, 2431)]),
    ("Beng", [(2432, 2559)]),
    ("Guru", [(2560, 2687)]),
    ("Gujr", [(2688, 2815)]),
    ("Orya", [(2816, 2943)]),
    ("Taml", [(2944, 3071)]),
    ("Telu", [(3072, 3199)]),
    ("Knda", [(3200, 3327)]),
    ("Mlym", [(3328, 3455)]),
    ("Thai", [(3584, 3711)]),
    ("Geor", [(4256, 4351), (7312, 7359)]),
    ("Cher", [(5024, 5119), (43888, 43967)]),
    ("Hira", [(12352, 12447)]),
    ("Kana", [(12448, 12543)]),
    ("Kore", [(44032, 55215), (12593, 12686)]),
    ("Ethi", [(4608, 4991)]),
    ("Hebr", [(1424, 1535)]),
    ("Grek", [(880, 1023)]),
    ("Hans", [(19968, 40959)]),
    ("Latn", [(65, 90), (97, 122), (192, 591), (7680, 7935)]),
]


def _char_script(cp: int) -> str | None:
    """Return the script name for a single Unicode codepoint, or None."""
    for script_id, ranges in SCRIPT_RANGES:
        for start, end in ranges:
            if start <= cp <= end:
                return "Jpan" if script_id in {"Hira", "Kana"} else script_id
    return None


def detect_script(text: str) -> str | None:
    """Detect the dominant Unicode script of a text string."""
    counts = Counter(_char_script(ord(ch)) for ch in text if not ch.isspace())
    counts.pop(None, None)
    if not counts:
        return None
    script, _ = counts.most_common(1)[0]
    return script


def detect_language(text: str) -> DetectionResult:
    """Detect the language of a text string using script and seeded lexical heuristics."""
    tokens = [t.casefold() for t in WORD_RE.findall(text)]
    token_set = set(tokens)
    top_script = detect_script(text)
    candidates: list[dict] = []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT l.language_id, l.name, l.family, l.branch, l.aliases_json, l.common_words_json,
                   GROUP_CONCAT(ls.script_id) AS scripts
            FROM languages l
            LEFT JOIN language_scripts ls ON ls.language_id = l.language_id
            GROUP BY l.language_id
            """
        ).fetchall()
        for row in rows:
            aliases = [a.casefold() for a in json.loads(row["aliases_json"])]
            common_words = [w.casefold() for w in json.loads(row["common_words_json"])]
            score = 0.0
            matched_words: list[str] = []
            if top_script and row["scripts"]:
                scripts = row["scripts"].split(",")
                if top_script in scripts:
                    score += 0.5
                elif top_script == "Hans" and ("Hans" in scripts or "Hant" in scripts):
                    score += 0.4
            for word in common_words:
                if word in token_set or word in text.casefold():
                    score += 0.12
                    matched_words.append(word)
            if matched_words:
                score += min(0.2, len(set(matched_words)) * 0.04)
            for alias in aliases:
                if alias in text.casefold():
                    score += 0.1
            if score > 0:
                candidates.append({
                    "language_id": row["language_id"],
                    "name": row["name"],
                    "family": row["family"],
                    "branch": row["branch"],
                    "score": round(min(score, 0.99), 3),
                    "matched_words": sorted(set(matched_words))[:8],
                })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    winner = candidates[0] if candidates else None
    confidence = winner["score"] if winner else 0.0
    rationale = (
        f"top_script={top_script}; lexical_and_script_heuristics={winner.get('matched_words', [])}"
        if winner else
        f"top_script={top_script}; no seeded candidate strong enough"
    )
    return DetectionResult(
        text=text,
        top_script=top_script,
        candidates=candidates[:10],
        winner_language_id=winner["language_id"] if winner else None,
        confidence=confidence,
        rationale=rationale,
    )
