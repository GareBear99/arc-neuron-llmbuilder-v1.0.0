
from __future__ import annotations

import json
import uuid
from pathlib import Path

from arc_lang.core.db import connect
from arc_lang.core.models import utcnow
from arc_lang.services.lineage import get_lineage
from arc_lang.services.system_status import get_system_status
from arc_lang.services.provider_registry import list_providers
from arc_lang.services.runtime_receipts import list_job_receipts
from arc_lang.services.provider_actions import list_provider_action_receipts
from arc_lang.services.package_lifecycle import list_translation_install_plans


def export_evidence_bundle(output_path: str, language_ids: list[str] | None = None, include_receipts: bool = True, include_runtime: bool = True, include_graph: bool = True) -> dict:
    """Export a full operator evidence bundle (system status, providers, lineage, receipts) to JSON."""
    language_ids = language_ids or []
    bundle = {
        "schema": "arc_language_module_evidence_bundle_v1",
        "exported_at": utcnow(),
        "system_status": get_system_status(),
        "providers": list_providers(),
    }
    if include_graph:
        bundle["lineage"] = {language_id: get_lineage(language_id) for language_id in language_ids}
    if include_runtime:
        bundle["install_plans"] = list_translation_install_plans(limit=200)
    if include_receipts:
        bundle["job_receipts"] = list_job_receipts(limit=200)
        bundle["provider_action_receipts"] = list_provider_action_receipts(limit=200)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    export_id = f"exp_{uuid.uuid4().hex[:12]}"
    summary = {
        "languages_exported": language_ids,
        "provider_count": len(bundle.get("providers", {}).get("providers", [])),
        "included_receipts": include_receipts,
        "included_runtime": include_runtime,
        "included_graph": include_graph,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO evidence_exports(export_id, output_path, include_receipts, include_runtime, include_graph, language_ids_json, summary_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_id,
                str(path),
                1 if include_receipts else 0,
                1 if include_runtime else 0,
                1 if include_graph else 0,
                json.dumps(language_ids, ensure_ascii=False),
                json.dumps(summary, ensure_ascii=False),
                utcnow(),
            ),
        )
        conn.commit()
    return {"ok": True, "export_id": export_id, "output_path": str(path), "summary": summary}
