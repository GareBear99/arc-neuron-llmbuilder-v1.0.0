
from __future__ import annotations

from arc_lang.core.db import connect
from arc_lang.services.policy import get_policy_snapshot
from arc_lang.services.provider_registry import list_providers
from arc_lang.services.stats import get_graph_stats


def _count(query: str, params: tuple = ()) -> int:
    with connect() as conn:
        row = conn.execute(query, params).fetchone()
    return int(row[0] or 0)


def get_system_status() -> dict:
    """Return a full system status snapshot: graph, providers, health, governance, receipts, policy."""
    stats = get_graph_stats()
    providers = list_providers().get("providers", [])
    provider_summary = {
        "total": len(providers),
        "total_registered": len(providers),
        "enabled": sum(1 for p in providers if p.get("enabled")),
        "disabled": sum(1 for p in providers if not p.get("enabled")),
        "local_only": sum(1 for p in providers if p.get("local_only")),
        "translation": sum(1 for p in providers if p.get("provider_type") == "translation"),
        "speech": sum(1 for p in providers if p.get("provider_type") == "speech"),
    }
    receipt_summary = {
        "runtime_receipts": _count("SELECT COUNT(*) FROM job_receipts"),
        "action_receipts": _count("SELECT COUNT(*) FROM provider_action_receipts"),
        "install_plans": _count("SELECT COUNT(*) FROM translation_install_plans"),
        "evidence_exports": _count("SELECT COUNT(*) FROM evidence_exports"),
    }
    governance_summary = {
        "language_submissions": _count("SELECT COUNT(*) FROM language_submissions"),
        "custom_lineage": _count("SELECT COUNT(*) FROM custom_lineage_assertions"),
        "reviews": _count("SELECT COUNT(*) FROM review_decisions"),
        "capabilities": _count("SELECT COUNT(*) FROM language_capabilities"),
        "pronunciation_profiles": _count("SELECT COUNT(*) FROM pronunciation_profiles"),
        "phonology_profiles": _count("SELECT COUNT(*) FROM phonology_profiles"),
        "transliteration_profiles": _count("SELECT COUNT(*) FROM transliteration_profiles"),
        "semantic_concepts": _count("SELECT COUNT(*) FROM semantic_concepts"),
        "language_variants": _count("SELECT COUNT(*) FROM language_variants"),
        "conflict_review_exports": _count("SELECT COUNT(*) FROM conflict_review_exports"),
        "coverage_reports": _count("SELECT COUNT(*) FROM coverage_reports"),
        "backend_manifests": _count("SELECT COUNT(*) FROM backend_manifests"),
        "corpus_manifests": _count("SELECT COUNT(*) FROM corpus_manifests"),
        "implementation_matrix_reports": _count("SELECT COUNT(*) FROM implementation_matrix_reports"),
    }
    health_summary = {
        "healthy": _count("SELECT COUNT(*) FROM (SELECT provider_name, MAX(created_at) AS latest FROM provider_health GROUP BY provider_name) lp JOIN provider_health ph ON ph.provider_name = lp.provider_name AND ph.created_at = lp.latest WHERE ph.status = 'healthy'"),
        "degraded": _count("SELECT COUNT(*) FROM (SELECT provider_name, MAX(created_at) AS latest FROM provider_health GROUP BY provider_name) lp JOIN provider_health ph ON ph.provider_name = lp.provider_name AND ph.created_at = lp.latest WHERE ph.status = 'degraded'"),
        "offline": _count("SELECT COUNT(*) FROM (SELECT provider_name, MAX(created_at) AS latest FROM provider_health GROUP BY provider_name) lp JOIN provider_health ph ON ph.provider_name = lp.provider_name AND ph.created_at = lp.latest WHERE ph.status = 'offline'"),
    }
    readiness_summary = []
    with connect() as conn:
        readiness_summary = [dict(r) for r in conn.execute("SELECT capability_name, maturity, COUNT(*) AS c FROM language_capabilities GROUP BY capability_name, maturity ORDER BY capability_name, maturity").fetchall()]
    status = "ready"
    if health_summary["offline"] > 0:
        status = "degraded"
    if provider_summary["enabled"] == 0:
        status = "bootstrap"
    return {
        "ok": True,
        "status": status,
        "graph": stats,
        "providers": provider_summary,
        "provider_summary": provider_summary,
        "provider_health": health_summary,
        "readiness_summary": readiness_summary,
        "governance": governance_summary,
        "receipts": receipt_summary,
        "policy": get_policy_snapshot(),
    }
