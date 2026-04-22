from __future__ import annotations

import importlib.util
from arc_lang.core.db import connect
from arc_lang.services.governance import list_language_capabilities
from arc_lang.services.provider_registry import get_provider_record, get_latest_provider_health, provider_is_usable
from arc_lang.services.translation_backends import ISO6393_TO_RUNTIME, list_builtin_translation_backends

MATURITY_ORDER = {"none": 0, "seeded": 1, "experimental": 2, "reviewed": 3, "production": 4}
READINESS_ORDER = {"blocked": 0, "theoretical": 1, "degraded": 2, "ready": 3}


def _language_row(language_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT language_id, iso639_3, name FROM languages WHERE language_id = ?",
            (language_id,),
        ).fetchone()
    return dict(row) if row else None


def _runtime_code_for_language(language_id: str) -> dict:
    row = _language_row(language_id)
    if not row:
        return {"language_id": language_id, "exists": False, "iso639_3": None, "runtime_code": None, "name": None}
    iso3 = row.get("iso639_3")
    return {
        "language_id": row["language_id"],
        "exists": True,
        "iso639_3": iso3,
        "runtime_code": ISO6393_TO_RUNTIME.get(iso3) or iso3,
        "name": row["name"],
    }


def _safe_argos_import():
    if importlib.util.find_spec("argostranslate") is None:
        return None, {"available": False, "reason": "dependency_missing", "dependency": "argostranslate"}
    try:
        from argostranslate import translate as argos_translate
        return argos_translate, {"available": True, "reason": "ok"}
    except Exception as e:
        return None, {"available": False, "reason": "dependency_failed", "details": f"{type(e).__name__}: {e}", "dependency": "argostranslate"}


def get_argos_local_diagnostics() -> dict:
    """Return diagnostic information for the argos_local optional translation backend."""
    argos_translate, meta = _safe_argos_import()
    result = {
        "ok": True,
        "provider_name": "argos_local",
        "backend_type": "translation",
        "dependency": meta,
        "installed_languages": [],
        "installed_pairs": [],
        "language_count": 0,
        "pair_count": 0,
    }
    if not meta["available"]:
        result["readiness"] = "blocked"
        return result
    try:
        installed = argos_translate.get_installed_languages()
    except Exception as e:
        result["dependency"] = {"available": False, "reason": "runtime_failed", "details": f"{type(e).__name__}: {e}", "dependency": "argostranslate"}
        result["readiness"] = "blocked"
        return result
    langs=[]
    pairs=[]
    for lang in installed:
        code = getattr(lang, 'code', None)
        name = getattr(lang, 'name', None)
        targets=[]
        try:
            translations = getattr(lang, 'translations_from', None)
            if translations is None:
                translations = []
            for trans in translations:
                to_lang = getattr(trans, 'to_lang', None)
                to_code = getattr(to_lang, 'code', None) if to_lang else None
                if to_code:
                    targets.append(to_code)
                    pairs.append({"source_runtime_code": code, "target_runtime_code": to_code})
        except Exception as e:
            result.setdefault("warnings", []).append(f"language_pair_scan_failed:{code}:{type(e).__name__}")
        langs.append({"runtime_code": code, "name": name, "target_runtime_codes": sorted(set(targets))})
    result["installed_languages"] = sorted(langs, key=lambda x: (x['runtime_code'] or ''))
    result["installed_pairs"] = sorted(pairs, key=lambda x: (x['source_runtime_code'] or '', x['target_runtime_code'] or ''))
    result["language_count"] = len(result["installed_languages"])
    result["pair_count"] = len(result["installed_pairs"])
    result["readiness"] = "ready" if result["pair_count"] else "degraded"
    return result


def get_provider_diagnostics(provider_name: str | None = None) -> dict:
    """Return diagnostic information for all providers, or a specific named provider."""
    if provider_name and provider_name == 'argos_local':
        return get_argos_local_diagnostics()
    if provider_name:
        rec = get_provider_record(provider_name)
        health = get_latest_provider_health(provider_name)
        usable = provider_is_usable(provider_name)
        return {"ok": True, "provider_name": provider_name, "provider": rec, "health": health, "usable": usable, "backend_specific": None}
    providers = []
    backend_names = {b['provider_name'] for b in list_builtin_translation_backends()['backends']}
    for name in sorted(backend_names | {'personaplex'}):
        if name == 'argos_local':
            providers.append(get_argos_local_diagnostics())
        else:
            providers.append(get_provider_diagnostics(name))
    return {"ok": True, "providers": providers}


def _capability_rows(language_id: str, capability_name: str, provider_name: str | None = None) -> list[dict]:
    caps = list_language_capabilities(language_id=language_id)['results']
    caps = [c for c in caps if c['capability_name'] == capability_name]
    if provider_name:
        caps = [c for c in caps if c['provider'] == provider_name]
    caps.sort(key=lambda c: (MATURITY_ORDER.get(c['maturity'], -1), c['confidence']), reverse=True)
    return caps


def _provider_ready_state(provider_name: str) -> tuple[str, list[str], dict | None]:
    notes=[]
    diag=None
    if provider_name == 'local_seed':
        return 'ready', ['Local seeded graph backend is always available once the DB is initialized.'], None
    if provider_name == 'mirror_mock':
        return 'ready', ['Mirror mock backend is built in and runtime-local.'], None
    if provider_name == 'argos_local':
        diag = get_argos_local_diagnostics()
        if not diag['dependency']['available']:
            return 'blocked', ['Argos local backend dependency is missing or failed.'], diag
        if diag['pair_count'] == 0:
            return 'degraded', ['Argos local backend is installed but no translation packages were detected.'], diag
        return 'ready', ['Argos local backend has installed language packages.'], diag
    usable = provider_is_usable(provider_name)
    diag = {"provider": get_provider_record(provider_name), "health": get_latest_provider_health(provider_name), "usable": usable}
    if not usable.get('usable'):
        return 'blocked', [f"Provider is not usable: {usable.get('reason')}"], diag
    if usable.get('reason') == 'provider_degraded':
        return 'degraded', ['Provider is marked degraded but still usable.'], diag
    return 'ready', ['Provider is registered and usable.'], diag


def get_translation_pair_readiness(source_language_id: str, target_language_id: str, provider_name: str | None = None) -> dict:
    """Return readiness verdict for a source→target translation pair via a named provider."""
    source = _runtime_code_for_language(source_language_id)
    target = _runtime_code_for_language(target_language_id)
    if not source['exists'] or not target['exists']:
        return {
            'ok': False,
            'error': 'language_not_found',
            'source_language': source,
            'target_language': target,
        }

    candidate_providers = [provider_name] if provider_name else sorted({
        *(c['provider'] for c in _capability_rows(source_language_id, 'translation')),
        *(c['provider'] for c in _capability_rows(target_language_id, 'translation')),
        'local_seed',
    })

    evaluations=[]
    for provider in [p for p in candidate_providers if p]:
        src_caps = _capability_rows(source_language_id, 'translation', provider)
        tgt_caps = _capability_rows(target_language_id, 'translation', provider)
        provider_state, provider_notes, provider_diag = _provider_ready_state(provider)
        notes=list(provider_notes)
        readiness='blocked'
        reasons=[]
        if not src_caps and not tgt_caps and provider != 'local_seed':
            reasons.append('no_translation_capability_records')
            notes.append('Neither source nor target language has a translation capability record for this provider.')
        else:
            if provider == 'local_seed':
                readiness = 'ready'
                reasons.append('builtin_local_seed_available')
            elif provider == 'mirror_mock':
                if source_language_id == target_language_id:
                    readiness = provider_state
                    reasons.append('same_language_identity_supported')
                else:
                    readiness = 'blocked'
                    reasons.append('mirror_requires_same_language')
                    notes.append('mirror_mock only supports same-language identity flows.')
            elif provider == 'argos_local':
                if not source.get('runtime_code') or not target.get('runtime_code'):
                    readiness = 'blocked'
                    reasons.append('runtime_code_unmapped')
                    notes.append('One or both languages are missing runtime code mappings for Argos local.')
                else:
                    diag = provider_diag or get_argos_local_diagnostics()
                    pair = any(p['source_runtime_code'] == source['runtime_code'] and p['target_runtime_code'] == target['runtime_code'] for p in diag.get('installed_pairs', []))
                    if pair:
                        readiness = provider_state if provider_state != 'blocked' else 'blocked'
                        reasons.append('installed_argos_pair_present')
                    elif diag['dependency']['available']:
                        readiness = 'degraded' if provider_state != 'blocked' else 'blocked'
                        reasons.append('installed_argos_pair_missing')
                        notes.append('Argos is present, but the exact source/target pair was not found among installed packages.')
                    else:
                        readiness = 'blocked'
                        reasons.append('argostranslate_dependency_missing')
            elif provider in {'argos_bridge', 'nllb_bridge'}:
                readiness = 'theoretical' if provider_state != 'blocked' else 'blocked'
                reasons.append('boundary_stub_only')
                notes.append('This provider is wired as a boundary stub; a live bridge is still required for execution.')
            else:
                readiness = provider_state
                reasons.append('provider_backed_capability_present')

        evaluations.append({
            'provider_name': provider,
            'readiness': readiness,
            'source_capabilities': src_caps,
            'target_capabilities': tgt_caps,
            'provider_diagnostics': provider_diag,
            'reasons': reasons,
            'notes': notes,
        })

    evaluations.sort(key=lambda e: (READINESS_ORDER.get(e['readiness'], -1), len(e['source_capabilities']) + len(e['target_capabilities'])), reverse=True)
    best = evaluations[0] if evaluations else None
    return {
        'ok': True,
        'source_language': source,
        'target_language': target,
        'best_provider': best,
        'evaluations': evaluations,
    }


def get_translation_readiness_matrix(target_language_id: str | None = None, provider_name: str | None = None, limit: int = 25) -> dict:
    """Return translation readiness across all known languages for a given provider."""
    with connect() as conn:
        if target_language_id:
            target_ids = [target_language_id]
        else:
            target_ids = [r['language_id'] for r in conn.execute(
                "SELECT DISTINCT language_id FROM language_capabilities WHERE capability_name = 'translation' ORDER BY language_id LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()]
        source_ids = [r['language_id'] for r in conn.execute(
            "SELECT DISTINCT language_id FROM language_capabilities WHERE capability_name = 'translation' ORDER BY language_id LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()]
    rows=[]
    for src in source_ids:
        for dst in target_ids:
            if src == dst and provider_name not in {None, 'mirror_mock', 'local_seed'}:
                continue
            readiness = get_translation_pair_readiness(src, dst, provider_name=provider_name)
            if readiness.get('ok'):
                rows.append({
                    'source_language_id': src,
                    'target_language_id': dst,
                    'best_provider_name': readiness['best_provider']['provider_name'] if readiness.get('best_provider') else None,
                    'readiness': readiness['best_provider']['readiness'] if readiness.get('best_provider') else 'blocked',
                })
    rows.sort(key=lambda r: (READINESS_ORDER.get(r['readiness'], -1), r['source_language_id'], r['target_language_id']), reverse=True)
    return {'ok': True, 'rows': rows, 'provider_name': provider_name, 'targets': target_ids}
