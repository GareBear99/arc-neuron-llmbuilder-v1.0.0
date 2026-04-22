from __future__ import annotations

import json
import subprocess
import sys
import uuid
from typing import Any

from arc_lang.core.db import connect
from arc_lang.core.models import BackendActionRequest, utcnow
from arc_lang.services.backend_diagnostics import _runtime_code_for_language, get_argos_local_diagnostics
from arc_lang.services.package_lifecycle import build_translation_install_plan
from arc_lang.services.provider_registry import provider_is_usable
from arc_lang.services.policy import get_policy_flag


def _record_action_receipt(provider_name: str, action_name: str, request_payload: dict, response_payload: dict, status: str, dry_run: bool, allow_mutation: bool, notes: list[str]) -> dict:
    receipt_id = f"act_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO provider_action_receipts (
                action_receipt_id, provider_name, action_name, status, dry_run,
                allow_mutation, request_payload_json, response_payload_json,
                notes_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                provider_name,
                action_name,
                status,
                1 if dry_run else 0,
                1 if allow_mutation else 0,
                json.dumps(request_payload, ensure_ascii=False),
                json.dumps(response_payload, ensure_ascii=False),
                json.dumps(notes, ensure_ascii=False),
                utcnow(),
            ),
        )
        conn.commit()
    return {
        "action_receipt_id": receipt_id,
        "provider_name": provider_name,
        "action_name": action_name,
        "status": status,
        "dry_run": dry_run,
        "allow_mutation": allow_mutation,
        "notes": notes,
    }


def list_provider_action_receipts(provider_name: str | None = None, action_name: str | None = None, limit: int = 50) -> dict:
    """List provider action receipts, optionally filtered by provider_name and action_name."""
    q = "SELECT * FROM provider_action_receipts WHERE 1=1"
    params: list[Any] = []
    if provider_name:
        q += " AND provider_name = ?"
        params.append(provider_name)
    if action_name:
        q += " AND action_name = ?"
        params.append(action_name)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    for row in rows:
        row["request_payload"] = json.loads(row.pop("request_payload_json"))
        row["response_payload"] = json.loads(row.pop("response_payload_json"))
        row["notes"] = json.loads(row.pop("notes_json"))
        row["dry_run"] = bool(row["dry_run"])
        row["allow_mutation"] = bool(row["allow_mutation"])
    return {"ok": True, "results": rows}


def _argos_action_catalog(source_language_id: str, target_language_id: str) -> list[dict[str, Any]]:
    plan = build_translation_install_plan(source_language_id, target_language_id, provider_name="argos_local")
    if not plan.get("ok"):
        return []
    source = _runtime_code_for_language(source_language_id)
    target = _runtime_code_for_language(target_language_id)
    src_code = source.get("runtime_code") or "<src_code>"
    dst_code = target.get("runtime_code") or "<dst_code>"
    pair = f"{src_code}->{dst_code}"
    return [
        {
            "action_name": "install_dependency",
            "provider_name": "argos_local",
            "available": plan["next_action"] == "install_dependency",
            "execution_mode": "shell_command",
            "summary": "Install the optional Argos Translate Python dependency.",
            "commands": [[sys.executable, "-m", "pip", "install", "argostranslate"]],
            "manual_steps": [
                "Install argostranslate into the same environment as arc-language-module.",
                "Rerun provider diagnostics after installation.",
            ],
        },
        {
            "action_name": "map_runtime_codes",
            "provider_name": "argos_local",
            "available": plan["next_action"] == "map_runtime_codes",
            "execution_mode": "manual",
            "summary": "Add or correct ISO639-3 to Argos runtime code mappings.",
            "commands": [],
            "manual_steps": [
                f"Add runtime code mappings for {source_language_id} and/or {target_language_id}.",
                "Update translation_backends.ISO6393_TO_RUNTIME or add a dedicated mapping source.",
                "Rebuild readiness after the mapping update.",
            ],
        },
        {
            "action_name": "install_language_pair",
            "provider_name": "argos_local",
            "available": plan["next_action"] == "install_language_pair",
            "execution_mode": "manual_or_shell",
            "summary": f"Install or import the Argos language pair for {pair}.",
            "commands": [
                [sys.executable, "-c", (
                    "import sys; "
                    "print('Provide a local Argos package file or URL for pair %s and install it through argostranslate.package APIs.')"
                ) % pair]
            ],
            "manual_steps": [
                f"Acquire an Argos package that supports {pair}.",
                "Install the package through argostranslate.package.install_from_path or equivalent tooling.",
                "Rerun translation readiness for the exact pair.",
            ],
        },
        {
            "action_name": "verify_ready",
            "provider_name": "argos_local",
            "available": plan["next_action"] == "ready_to_execute",
            "execution_mode": "builtin",
            "summary": f"Verify that Argos is locally ready for pair {pair}.",
            "commands": [],
            "manual_steps": [
                "Run provider diagnostics and readiness again to confirm the pair remains installed.",
            ],
        },
    ]


def _bridge_action_catalog(provider_name: str) -> list[dict[str, Any]]:
    return [
        {
            "action_name": "configure_live_bridge",
            "provider_name": provider_name,
            "available": True,
            "execution_mode": "manual",
            "summary": f"Configure the live bridge for provider {provider_name}.",
            "commands": [],
            "manual_steps": [
                f"Register a real adapter implementation for {provider_name}.",
                "Set provider health to healthy once the bridge is reachable.",
                "Keep the provider in dry-run mode until real end-to-end tests pass.",
            ],
        }
    ]


def build_provider_action_catalog(source_language_id: str, target_language_id: str, provider_name: str) -> dict:
    """Build the available action catalog for a provider and language pair."""
    if provider_name == "argos_local":
        actions = _argos_action_catalog(source_language_id, target_language_id)
    elif provider_name in {"argos_bridge", "nllb_bridge"}:
        actions = _bridge_action_catalog(provider_name)
    else:
        actions = []
    return {
        "ok": True,
        "provider_name": provider_name,
        "source_language_id": source_language_id,
        "target_language_id": target_language_id,
        "actions": actions,
    }


def _execute_shell_command(command: list[str]) -> dict:
    proc = subprocess.run(command, capture_output=True, text=True)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": command,
    }


def execute_provider_action(req: BackendActionRequest) -> dict:
    """Execute a provider action (dry-run by default, mutation requires allow_mutation=True)."""
    health = provider_is_usable(req.provider_name)
    catalog = build_provider_action_catalog(req.source_language_id, req.target_language_id, req.provider_name)
    actions = {a["action_name"]: a for a in catalog["actions"]}
    action_name = req.action_name
    if not action_name:
        plan = build_translation_install_plan(req.source_language_id, req.target_language_id, provider_name=req.provider_name)
        inferred = plan.get("next_action")
        if inferred == "ready_to_execute":
            inferred = "verify_ready"
        action_name = inferred
    action = actions.get(action_name)
    if not action:
        response = {"ok": False, "error": "provider_action_unknown", "known_actions": sorted(actions)}
        receipt = _record_action_receipt(req.provider_name, action_name or "unknown", req.model_dump(), response, "failed", req.dry_run, req.allow_mutation, ["Requested action is not available for this provider."])
        response["receipt"] = receipt
        return response

    notes = list(req.notes)
    if req.provider_name not in {"argos_local", "local_seed", "mirror_mock"} and not health.get("usable"):
        notes.append("Provider is currently unhealthy or disabled; action remains planning-only.")

    if req.allow_mutation and not get_policy_flag('allow_mutation_actions', False):
        response = {'ok': False, 'error': 'provider_action_mutation_blocked_by_policy', 'notes': ['Policy allow_mutation_actions=false blocks mutating provider actions.']}
        receipt = _record_action_receipt(req.provider_name, action_name, req.model_dump(), response, 'blocked', req.dry_run, req.allow_mutation, response['notes'])
        response['receipt'] = receipt
        return response

    response: dict[str, Any] = {
        "ok": True,
        "provider_name": req.provider_name,
        "action_name": action_name,
        "dry_run": req.dry_run,
        "allow_mutation": req.allow_mutation,
        "execution_mode": action["execution_mode"],
        "summary": action["summary"],
        "commands": action["commands"],
        "manual_steps": action["manual_steps"],
        "provider_health": health,
    }

    status = "planned"
    if req.dry_run:
        status = "dry_run"
        notes.append("Action was not applied because dry_run=True.")
    else:
        if not req.allow_mutation and action["execution_mode"] in {"shell_command", "manual_or_shell"}:
            status = "blocked"
            response["ok"] = False
            response["error"] = "provider_action_mutation_blocked"
            notes.append("Set allow_mutation=True to permit host-changing shell actions.")
        elif action_name == "install_dependency" and action["execution_mode"] == "shell_command":
            shell = _execute_shell_command(action["commands"][0])
            response["shell_result"] = shell
            if shell["returncode"] == 0:
                status = "applied"
                notes.append("Dependency installation command completed.")
            else:
                status = "failed"
                response["ok"] = False
                response["error"] = "provider_action_shell_failed"
                notes.append("Dependency installation command failed.")
        elif action_name == "verify_ready":
            response["verification"] = build_translation_install_plan(req.source_language_id, req.target_language_id, provider_name=req.provider_name)
            status = "verified"
            notes.append("Readiness was re-evaluated for the requested provider and pair.")
        else:
            status = "manual_required"
            notes.append("This action currently requires a human or external installer bridge.")
            if req.package_ref:
                response["package_ref"] = req.package_ref

    receipt = _record_action_receipt(req.provider_name, action_name, req.model_dump(), response, status, req.dry_run, req.allow_mutation, notes)
    response["receipt"] = receipt
    return response
