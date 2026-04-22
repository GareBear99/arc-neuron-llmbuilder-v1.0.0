from __future__ import annotations

import json
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow
from arc_lang.services.backend_diagnostics import (
    get_argos_local_diagnostics,
    get_translation_pair_readiness,
    _runtime_code_for_language,
)


def _pair_note_summary(readiness_result: dict) -> str:
    top = readiness_result.get('best_provider') or {}
    provider = top.get('provider') or readiness_result.get('provider_name') or 'unknown'
    readiness = top.get('readiness') or readiness_result.get('readiness') or 'unknown'
    return f"{provider}:{readiness}"


def build_translation_install_plan(source_language_id: str, target_language_id: str, provider_name: str = 'argos_local') -> dict:
    """Generate a translation install plan for a source→target pair and provider."""
    readiness = get_translation_pair_readiness(source_language_id, target_language_id, provider_name=provider_name)
    if not readiness.get('ok'):
        return readiness

    source = readiness['source_language']
    target = readiness['target_language']
    top = readiness.get('best_provider') or {}
    plan_steps: list[str] = []
    warnings: list[str] = []
    missing: dict[str, list[str] | None] = {
        'dependencies': [],
        'runtime_codes': [],
        'language_pairs': [],
    }

    if provider_name == 'local_seed':
        plan_steps.append('Initialize the database and ingest the common seed pack.')
        plan_steps.append('Use local_seed for seeded phrase and lexeme translation only.')
        next_action = 'no_install_required'
        readiness_state = 'ready'
    elif provider_name == 'mirror_mock':
        plan_steps.append('No package installation is required for mirror_mock.')
        plan_steps.append('Use this backend only for same-language identity or pipeline tests.')
        next_action = 'no_install_required'
        readiness_state = top.get('readiness', 'ready')
    elif provider_name == 'argos_local':
        diag = get_argos_local_diagnostics()
        src_code = source.get('runtime_code')
        dst_code = target.get('runtime_code')
        readiness_state = top.get('readiness', diag.get('readiness', 'blocked'))
        if not diag['dependency']['available']:
            missing['dependencies'].append('argostranslate')
            plan_steps.append('Install the optional Python dependency: pip install argostranslate')
            plan_steps.append('After installation, rerun provider diagnostics for argos_local.')
            next_action = 'install_dependency'
        elif not src_code or not dst_code:
            if not src_code:
                missing['runtime_codes'].append(source_language_id)
            if not dst_code:
                missing['runtime_codes'].append(target_language_id)
            plan_steps.append('Add or correct runtime language code mappings for the requested languages.')
            plan_steps.append('Update ISO639-3 to Argos runtime code mappings before attempting package installation.')
            next_action = 'map_runtime_codes'
        else:
            pair_present = any(
                p['source_runtime_code'] == src_code and p['target_runtime_code'] == dst_code
                for p in diag.get('installed_pairs', [])
            )
            if pair_present:
                plan_steps.append(f'Argos language pair {src_code}->{dst_code} is already installed locally.')
                plan_steps.append('Run the translation request live with provider argos_local.')
                next_action = 'ready_to_execute'
                readiness_state = 'ready'
            else:
                missing['language_pairs'].append(f'{src_code}->{dst_code}')
                plan_steps.append(f'Install or import the Argos package for pair {src_code}->{dst_code}.')
                plan_steps.append('After package installation, rerun translation-readiness for this exact pair.')
                if diag.get('language_count', 0) == 0:
                    warnings.append('Argos dependency is present but no installed languages were detected.')
                next_action = 'install_language_pair'
                readiness_state = 'degraded' if diag['dependency']['available'] else 'blocked'
    else:
        plan_steps.append(f'{provider_name} is a boundary or external backend in this package.')
        plan_steps.append('Register a live bridge adapter or keep this provider in dry-run mode.')
        next_action = 'configure_live_bridge'
        readiness_state = top.get('readiness', 'theoretical')
        if readiness_state == 'blocked':
            warnings.append('Provider health or registration currently blocks execution.')

    return {
        'ok': True,
        'provider_name': provider_name,
        'source_language': source,
        'target_language': target,
        'readiness': readiness_state,
        'next_action': next_action,
        'summary': _pair_note_summary(readiness),
        'steps': plan_steps,
        'warnings': warnings,
        'missing': missing,
        'readiness_snapshot': readiness,
    }


def record_translation_install_plan(source_language_id: str, target_language_id: str, provider_name: str = 'argos_local', notes: list[str] | None = None) -> dict:
    """Record a translation install plan in the database."""
    plan = build_translation_install_plan(source_language_id, target_language_id, provider_name=provider_name)
    if not plan.get('ok'):
        return plan
    plan_id = f'plan_{uuid.uuid4().hex[:12]}'
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO translation_install_plans (
                plan_id, provider_name, source_language_id, target_language_id, readiness,
                next_action, steps_json, warnings_json, missing_json, notes_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                provider_name,
                source_language_id,
                target_language_id,
                plan['readiness'],
                plan['next_action'],
                json.dumps(plan['steps'], ensure_ascii=False),
                json.dumps(plan['warnings'], ensure_ascii=False),
                json.dumps(plan['missing'], ensure_ascii=False),
                json.dumps(notes or [], ensure_ascii=False),
                utcnow(),
            ),
        )
        conn.commit()
    return {'ok': True, 'plan_id': plan_id, 'plan': plan}


def list_translation_install_plans(provider_name: str | None = None, source_language_id: str | None = None, target_language_id: str | None = None, limit: int = 50) -> dict:
    """List translation install plans, optionally filtered by provider, source, and target language."""
    q = "SELECT * FROM translation_install_plans WHERE 1=1"
    params: list[object] = []
    if provider_name:
        q += " AND provider_name = ?"
        params.append(provider_name)
    if source_language_id:
        q += " AND source_language_id = ?"
        params.append(source_language_id)
    if target_language_id:
        q += " AND target_language_id = ?"
        params.append(target_language_id)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    for row in rows:
        row['steps'] = json.loads(row.pop('steps_json'))
        row['warnings'] = json.loads(row.pop('warnings_json'))
        row['missing'] = json.loads(row.pop('missing_json'))
        row['notes'] = json.loads(row.pop('notes_json'))
    return {'ok': True, 'results': rows}
