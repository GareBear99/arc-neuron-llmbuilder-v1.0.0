from __future__ import annotations

import json
import uuid
from collections import Counter

from arc_lang.core.db import connect
from arc_lang.core.models import AliasUpsertRequest, CapabilityUpdateRequest, utcnow
from arc_lang.services.aliases import upsert_language_alias
from arc_lang.services.governance import set_language_capability
from arc_lang.services.phonology import upsert_phonology_profile
from arc_lang.services.pronunciation import upsert_pronunciation_profile
from arc_lang.services.transliteration import BASIC_MAPS, upsert_transliteration_profile

CORE_CAPABILITIES = [
    "translation_seeded_phrases",
    "pronunciation_hint",
    "phonology_hint",
    "transliteration_to_latn",
    "runtime_translation",
    "runtime_speech",
]

NON_RUNTIME_CAPABILITIES = {"runtime_translation", "runtime_speech"}


def _lang_rows(language_ids: list[str] | None = None) -> list[dict]:
    with connect() as conn:
        if language_ids:
            placeholders = ",".join("?" for _ in language_ids)
            rows = conn.execute(
                f"SELECT * FROM languages WHERE language_id IN ({placeholders}) ORDER BY language_id", tuple(language_ids)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM languages ORDER BY language_id").fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["aliases"] = json.loads(item.get("aliases_json") or "[]")
        item["common_words"] = json.loads(item.get("common_words_json") or "[]")
        out.append(item)
    return out


def _language_surface_snapshot(conn, language_id: str) -> dict:
    phrase_count = conn.execute(
        "SELECT COUNT(*) AS c FROM phrase_translations WHERE language_id = ?", (language_id,)
    ).fetchone()["c"]
    alias_rows = [dict(r) for r in conn.execute(
        "SELECT alias, alias_type FROM language_aliases WHERE language_id = ?", (language_id,)
    ).fetchall()]
    scripts = [r["script_id"] for r in conn.execute(
        "SELECT script_id FROM language_scripts WHERE language_id = ? ORDER BY script_id", (language_id,)
    ).fetchall()]
    pron = conn.execute(
        "SELECT COUNT(*) AS c FROM pronunciation_profiles WHERE language_id = ?", (language_id,)
    ).fetchone()["c"]
    phon = conn.execute(
        "SELECT COUNT(*) AS c FROM phonology_profiles WHERE language_id = ?", (language_id,)
    ).fetchone()["c"]
    translit = [dict(r) for r in conn.execute(
        "SELECT source_script, target_script FROM transliteration_profiles WHERE language_id = ?", (language_id,)
    ).fetchall()]
    caps = [dict(r) for r in conn.execute(
        "SELECT capability_name, maturity, provider FROM language_capabilities WHERE language_id = ?", (language_id,)
    ).fetchall()]
    return {
        "phrase_count": phrase_count,
        "alias_rows": alias_rows,
        "scripts": scripts,
        "pronunciation_count": pron,
        "phonology_count": phon,
        "transliterations": translit,
        "capabilities": caps,
    }


def _insert_candidate(conn, scan_id: str, language_id: str, surface_type: str, payload: dict, rationale: str,
                      confidence: float, source_name: str, source_ref: str | None = None) -> str:
    now = utcnow()
    candidate_id = f"sfc_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO self_fill_candidates
        (candidate_id, scan_id, language_id, surface_type, payload_json, rationale, confidence, source_name, source_ref, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (candidate_id, scan_id, language_id, surface_type, json.dumps(payload, ensure_ascii=False, sort_keys=True), rationale,
         confidence, source_name, source_ref, "staged", now, now),
    )
    return candidate_id


def scan_self_fill_gaps(language_ids: list[str] | None = None, stage_candidates: bool = True,
                        source_name: str = "autofill_gap_scan") -> dict:
    languages = _lang_rows(language_ids)
    scan_id = f"sfs_{uuid.uuid4().hex[:12]}"
    staged = []
    summary_counter = Counter()
    language_summaries = []
    now = utcnow()
    with connect() as conn:
        for lang in languages:
            snap = _language_surface_snapshot(conn, lang["language_id"])
            missing = []
            alias_texts = {a["alias"] for a in snap["alias_rows"]}
            for alias in lang["aliases"]:
                if alias not in alias_texts:
                    missing.append({"surface_type": "alias", "payload": {
                        "alias": alias,
                        "alias_type": "alias",
                        "normalized_form": alias.casefold().strip(),
                        "script_id": None,
                        "region_hint": None,
                    }, "rationale": "language alias exists in canonical language row but has not been normalized into language_aliases"})
            if snap["pronunciation_count"] == 0:
                example_word = (lang["common_words"][:1] or [lang["name"]])[0]
                missing.append({"surface_type": "pronunciation_profile", "payload": {
                    "profile_kind": "autofill_seed",
                    "romanization_scheme": "native_or_latn_bridge",
                    "ipa_hint": None,
                    "examples": {example_word: example_word},
                    "notes": "autofill candidate: bootstrap pronunciation layer pending review",
                }, "rationale": "language has no pronunciation profile"})
            if snap["phonology_count"] == 0:
                missing.append({"surface_type": "phonology_profile", "payload": {
                    "notation_system": "broad",
                    "broad_ipa": None,
                    "stress_policy": None,
                    "syllable_template": None,
                    "examples": {},
                    "notes": "autofill candidate: bootstrap phonology layer pending review",
                }, "rationale": "language has no phonology profile"})
            translit_pairs = {(t["source_script"], t["target_script"]) for t in snap["transliterations"]}
            for script_id in snap["scripts"]:
                if script_id != "Latn" and (script_id, "Latn") not in translit_pairs:
                    coverage = "basic_seeded_mapping" if (script_id, "Latn") in BASIC_MAPS else "external_required"
                    missing.append({"surface_type": "transliteration_profile", "payload": {
                        "source_script": script_id,
                        "target_script": "Latn",
                        "scheme_name": f"autofill_{script_id.lower()}_to_latn",
                        "coverage": coverage,
                        "example_in": None,
                        "example_out": None,
                        "notes": f"autofill candidate: transliteration bridge for {script_id}->Latn",
                    }, "rationale": f"language uses non-Latin script {script_id} but lacks a transliteration profile to Latin"})
            existing_caps = {(c["capability_name"], c["provider"]) for c in snap["capabilities"]}
            for cap in CORE_CAPABILITIES:
                if (cap, "local") in existing_caps:
                    continue
                maturity = "none"
                notes = "autofill candidate"
                if cap == "translation_seeded_phrases":
                    maturity = "seeded" if snap["phrase_count"] > 0 else "none"
                    notes = f"phrase_count={snap['phrase_count']}"
                elif cap == "pronunciation_hint":
                    maturity = "seeded" if snap["pronunciation_count"] > 0 else "seeded"
                elif cap == "phonology_hint":
                    maturity = "seeded" if snap["phonology_count"] > 0 else "seeded"
                elif cap == "transliteration_to_latn":
                    maturity = "seeded" if any(t["target_script"] == "Latn" for t in snap["transliterations"]) or any(s != 'Latn' for s in snap['scripts']) else "reviewed"
                elif cap in NON_RUNTIME_CAPABILITIES:
                    maturity = "none"
                    notes = "runtime capability intentionally left none until provider/runtime registration"
                missing.append({"surface_type": "capability", "payload": {
                    "capability_name": cap,
                    "maturity": maturity,
                    "provider": "local",
                    "notes": notes,
                    "confidence": 0.6 if maturity == "none" else 0.72,
                }, "rationale": f"language is missing canonical capability row for {cap}"})
            if stage_candidates:
                for item in missing:
                    conf = item["payload"].get("confidence", 0.66)
                    candidate_id = _insert_candidate(conn, scan_id, lang["language_id"], item["surface_type"], item["payload"], item["rationale"], conf, source_name)
                    staged.append(candidate_id)
                    summary_counter[item["surface_type"]] += 1
            language_summaries.append({
                "language_id": lang["language_id"],
                "name": lang["name"],
                "missing_count": len(missing),
                "missing_by_surface": Counter(m["surface_type"] for m in missing),
            })
        summary = {
            "language_count": len(languages),
            "candidate_count": len(staged),
            "surface_counts": dict(summary_counter),
        }
        conn.execute(
            "INSERT INTO self_fill_scan_runs (scan_id, mode, language_ids_json, summary_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (scan_id, "gap_scan", json.dumps(language_ids or [], ensure_ascii=False), json.dumps(summary, ensure_ascii=False, sort_keys=True), now),
        )
        conn.commit()
    return {
        "ok": True,
        "scan_id": scan_id,
        "summary": summary,
        "language_summaries": [
            {**entry, "missing_by_surface": dict(entry["missing_by_surface"])} for entry in language_summaries
        ],
    }


def list_self_fill_candidates(status: str | None = None, language_id: str | None = None, surface_type: str | None = None, limit: int = 200) -> dict:
    query = "SELECT * FROM self_fill_candidates"
    clauses = []
    params: list = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if language_id:
        clauses.append("language_id = ?")
        params.append(language_id)
    if surface_type:
        clauses.append("surface_type = ?")
        params.append(surface_type)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
    for row in rows:
        row["payload"] = json.loads(row.pop("payload_json") or "{}")
    return {"ok": True, "count": len(rows), "results": rows}


def list_self_fill_scan_runs(limit: int = 50) -> dict:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM self_fill_scan_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]
    for row in rows:
        row["language_ids"] = json.loads(row.pop("language_ids_json") or "[]")
        row["summary"] = json.loads(row.pop("summary_json") or "{}")
    return {"ok": True, "results": rows}


def promote_self_fill_candidate(candidate_id: str, reviewer: str = "autofill_promoter") -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM self_fill_candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
    candidate = dict(row)
    if candidate["status"] not in {"staged", "reviewed"}:
        return {"ok": False, "error": "candidate_not_promotable", "status": candidate["status"]}
    payload = json.loads(candidate["payload_json"] or "{}")
    result = None
    target_type = candidate["surface_type"]
    target_id = None
    if target_type == "alias":
        result = upsert_language_alias(AliasUpsertRequest(
            language_id=candidate["language_id"],
            alias=payload["alias"],
            alias_type=payload.get("alias_type", "alias"),
            normalized_form=payload.get("normalized_form"),
            script_id=payload.get("script_id"),
            region_hint=payload.get("region_hint"),
            source_name=candidate["source_name"],
            source_ref=candidate.get("source_ref"),
            confidence=candidate["confidence"],
            notes=f"promoted from self-fill by {reviewer}",
        ))
        target_id = result.get("alias_id")
    elif target_type == "capability":
        result = set_language_capability(CapabilityUpdateRequest(
            language_id=candidate["language_id"],
            capability_name=payload["capability_name"],
            maturity=payload["maturity"],
            confidence=payload.get("confidence", candidate["confidence"]),
            provider=payload.get("provider", "local"),
            notes=payload.get("notes", "promoted from self-fill"),
        ))
        target_id = result.get("capability_id")
    elif target_type == "pronunciation_profile":
        result = upsert_pronunciation_profile(
            candidate["language_id"],
            payload.get("profile_kind", "autofill_seed"),
            payload.get("romanization_scheme"),
            payload.get("ipa_hint"),
            payload.get("examples", {}),
            notes=payload.get("notes", "promoted from self-fill"),
        )
        target_id = result.get("profile_id")
    elif target_type == "phonology_profile":
        result = upsert_phonology_profile(
            candidate["language_id"],
            payload.get("notation_system", "broad"),
            broad_ipa=payload.get("broad_ipa"),
            stress_policy=payload.get("stress_policy"),
            syllable_template=payload.get("syllable_template"),
            examples=payload.get("examples", {}),
            notes=payload.get("notes", "promoted from self-fill"),
        )
        target_id = result.get("profile_id")
    elif target_type == "transliteration_profile":
        result = upsert_transliteration_profile(
            candidate["language_id"],
            payload["source_script"],
            payload.get("target_script", "Latn"),
            payload.get("scheme_name", "autofill_to_latn"),
            payload.get("coverage", "external_required"),
            example_in=payload.get("example_in"),
            example_out=payload.get("example_out"),
            notes=payload.get("notes", "promoted from self-fill"),
        )
        target_id = result.get("profile_id")
    else:
        return {"ok": False, "error": "unsupported_surface_type", "surface_type": target_type}
    now = utcnow()
    promotion_id = f"sfp_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            "UPDATE self_fill_candidates SET status = ?, updated_at = ? WHERE candidate_id = ?",
            ("promoted" if result.get("ok") else "promotion_failed", now, candidate_id),
        )
        conn.execute(
            "INSERT INTO self_fill_promotions (promotion_id, candidate_id, target_type, target_id, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (promotion_id, candidate_id, target_type, target_id, "ok" if result.get("ok") else "failed", f"reviewer={reviewer}", now),
        )
        conn.commit()
    return {"ok": True, "promotion_id": promotion_id, "candidate_id": candidate_id, "target_type": target_type, "target_id": target_id, "result": result}


def reject_self_fill_candidate(candidate_id: str, reviewer: str = "autofill_reviewer", notes: str = "") -> dict:
    now = utcnow()
    with connect() as conn:
        row = conn.execute("SELECT candidate_id FROM self_fill_candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
        conn.execute("UPDATE self_fill_candidates SET status = ?, updated_at = ? WHERE candidate_id = ?", ("rejected", now, candidate_id))
        conn.execute(
            "INSERT INTO self_fill_promotions (promotion_id, candidate_id, target_type, target_id, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"sfp_{uuid.uuid4().hex[:12]}", candidate_id, "review", None, "rejected", f"reviewer={reviewer}; notes={notes}", now),
        )
        conn.commit()
    return {"ok": True, "candidate_id": candidate_id, "status": "rejected"}
